"""
This file sends packets to GSE and Frontend api
It should only have devices controlled by a human
"""

import backend.includes_python.process_logging as slogger

try:
    import hid
except (ImportError, RuntimeError) as e:
    """
    if the hid module fails to import and you dont want to use a hid controller, then no harm so just warn in slogger
    if you want the hid device (controller = rpi_gpio_device)
    """
    error_message = "This should not have run, make sure you set controller = rpi_gpio_device or pygame_device (config.ini) or check your hid install is correct"
    slogger.error(
        f"hid is not correctly installed: {e}. This is okay if your using rpi_gpio_device or pygame_device (check config.ini)"
    )

    class hid:
        def Device():
            raise NotImplementedError(error_message)


import pygame
import zmq
import os
import time
from backend import device_emulator
from backend.includes_python import service_helper
from backend.includes_python.timers import RepeatingTimer
from backend.includes_python.devices.control_device_manager import (
    ControlDeviceManager,
)
from backend.includes_python.devices.control_device import ControlDevice
from config import config

# Wait LINGER_TIME_MS before giving up on push request
LINGER_TIME_MS = 300

# path to the socket that gets forwarded to GSE in the c++ server
GSE_SOCKET_PATH = os.path.abspath(
    os.path.join(os.path.sep, "tmp", "gcs_rocket_pendant_pull.sock")
)

# path to the socket read by frontend api
FRONTEND_SOCKET_PATH = os.path.abspath(
    os.path.join(os.path.sep, "tmp", "gcs_pendant_frontend_pub.sock")
)


def get_control_device() -> ControlDevice:
    # fmt: off
    manager = ControlDeviceManager()

    def hybrid_import() -> type[ControlDevice]:
        from backend.includes_python.devices.pygame_devices import HybridPygamePendant
        return HybridPygamePendant

    manager.add_managed_device("hybrid_device", hybrid_import)

    def rpi_import() -> type[ControlDevice]:
        from backend.includes_python.devices.rpi_gpio_device import RPI_GPIO_Device
        return RPI_GPIO_Device

    manager.add_managed_device("rpi_gpio_device",rpi_import)

    def f710_import() -> type[ControlDevice]:
        from backend.includes_python.devices.pygame_devices import LogitechGamepadF710
        return LogitechGamepadF710

    manager.add_managed_device("f710", f710_import)

    # TEMPORARY: idk why this got left out but i adding it back
    def emulated_import() -> Type[ControlDevice]:
        from backend.includes_python.devices.emulated_device import Emulated_Device
        return Emulated_Device

    manager.add_managed_device("emulated_device", emulated_import)

    return manager.get_control_device()
    # fmt: on


def send_packet() -> None:
    context = zmq.Context()

    gse_packet_send_timer = RepeatingTimer(0.05)
    frontend_packet_send_timer = RepeatingTimer(0.5)
    gse_complain_timer = RepeatingTimer(5)
    frontend_complain_timer = RepeatingTimer(5)

    controller = get_control_device()

    # define sockets first to ensure they are not undefined
    gse_push_socket = context.socket(zmq.PUSH)
    frontend_pub_socket = context.socket(zmq.PUB)

    try:
        gse_push_socket.setsockopt(zmq.LINGER, LINGER_TIME_MS)
        gse_push_socket.setsockopt(
            zmq.SNDHWM, 1
        )  # Limit send buffer to 1 message
        gse_push_socket.connect(f"ipc://{GSE_SOCKET_PATH}")

        frontend_pub_socket.setsockopt(zmq.LINGER, LINGER_TIME_MS)
        frontend_pub_socket.setsockopt(
            zmq.SNDHWM, 1
        )  # Limit send buffer to 1 message
        frontend_pub_socket.bind(f"ipc://{FRONTEND_SOCKET_PATH}")

        previous_packet = {}

        while not service_helper.time_to_stop():
            # Get values to pass to emulator
            # These states are validated, error checked and include fallback
            pendant_state_dict = controller.get_state_table().get_gse_states()
            state_command = device_emulator.GCStoGSEStateCMD(
                **pendant_state_dict
            )

            change_in_pendant_data = previous_packet != pendant_state_dict
            previous_packet = pendant_state_dict

            # NEVER SEND PACKET FROM THE EMULATED_DEVICE TO THE SERVER
            if (
                gse_packet_send_timer.time_has_passed()
                or change_in_pendant_data
            ):
                # send to c++ server to forward to GSE
                try:
                    gse_push_socket.send(
                        state_command.get_payload_bytes(EXTERNAL=True),
                        flags=zmq.NOBLOCK,
                    )
                except zmq.ZMQError:
                    # Queue is likely full
                    if gse_complain_timer.time_has_passed():
                        slogger.warning(
                            "Server ZMQ Push socket is full. Cannot send data until it is emptied in server."
                        )

            if (
                frontend_packet_send_timer.time_has_passed()
                or change_in_pendant_data
            ):
                # send to frontend api
                try:
                    frontend_pub_socket.send_json(
                        pendant_state_dict,
                        flags=zmq.NOBLOCK,
                    )
                except zmq.ZMQError as e:
                    # Queue is likely full
                    if frontend_complain_timer.time_has_passed():
                        slogger.warning(
                            f"Frontend ZMQ Push socket is likely full. error: {e}"
                        )

            # No need to go full blast.
            time.sleep(0.05)
    finally:
        slogger.debug("Packet sender closing socket")
        gse_push_socket.close()
        frontend_pub_socket.close()
        slogger.debug("Packet sender closed socket")
        slogger.debug(f"Packet sender closing context (<{LINGER_TIME_MS}ms)")
        context.term()
        slogger.debug("Packet sender thread resources cleaned up")
        slogger.debug("Cleaning up controller")
        controller.cleanup()
        slogger.debug("Cleaned up controller")


def main() -> None:
    device_emulator.MockPacket.initialize_settings(
        config.get_config()['emulation'])
    slogger.debug("Starting pendant emulator")

    # global packet_thread
    # packet_thread = threading.Thread(target=send_packet)
    # packet_thread.start()
    send_packet()


if __name__ == "__main__":
    main()
