"""
This file sends packets to Frontend api
Its safe to have any type of device, automatic or not here
"""


import backend.includes_python.process_logging as slogger
import zmq
import os
import time
import backend.device_emulator as device_emulator
import backend.includes_python.service_helper as service_helper
from backend.includes_python.timers import RepeatingTimer
from backend.includes_python.devices.control_device_manager import (
    ControlDeviceManager,
)
from backend.includes_python.devices.control_device import ControlDevice

import config.config as config
from typing import Type

# Wait LINGER_TIME_MS before giving up on push request
LINGER_TIME_MS = 300

# path to the socket read by frontend api
FRONTEND_SOCKET_PATH = os.path.abspath(
    os.path.join(os.path.sep, "tmp", "gcs_pendant_frontend_pub.sock")
)


def get_control_device():
    # fmt: off
    manager = ControlDeviceManager()

    def hybrid_import() -> Type[ControlDevice]:
        from backend.includes_python.devices.pygame_devices import HybridPygamePendant
        return HybridPygamePendant

    manager.add_managed_device("hybrid_device", hybrid_import)

    def rpi_import() -> Type[ControlDevice]:
        from backend.includes_python.devices.rpi_gpio_device import RPI_GPIO_Device
        return RPI_GPIO_Device

    manager.add_managed_device("rpi_gpio_device",rpi_import)

    def f710_import() -> Type[ControlDevice]:
        from backend.includes_python.devices.pygame_devices import LogitechGamepadF710
        return LogitechGamepadF710

    manager.add_managed_device("f710", f710_import)

    def emulated_import() -> Type[ControlDevice]:
        from backend.includes_python.devices.emulated_device import Emulated_Device
        return Emulated_Device

    manager.add_managed_device("emulated_device", emulated_import)

    def hid_import() -> Type[ControlDevice]:
        from backend.includes_python.devices.hid_device import HID_Device
        return HID_Device

    manager.add_managed_device("hid_device", hid_import)

    # only really used by me (Xavier)
    def thrustmaster_import() -> Type[ControlDevice]:
        from backend.includes_python.devices.pygame_devices import ThrustmasterAirbusFlightStick
        return ThrustmasterAirbusFlightStick

    manager.add_managed_device("thrustmaster", thrustmaster_import)

    return manager.get_control_device()
    # fmt: on


def send_packet():
    context = zmq.Context()

    frontend_packet_send_timer = RepeatingTimer(0.5)
    frontend_complain_timer = RepeatingTimer(5)

    controller = get_control_device()

    # define socket first to ensure its not undefined
    frontend_pub_socket = context.socket(zmq.PUB)

    try:
        frontend_pub_socket.setsockopt(zmq.LINGER, LINGER_TIME_MS)
        frontend_pub_socket.setsockopt(zmq.SNDHWM, 1)
        frontend_pub_socket.bind(f"ipc://{FRONTEND_SOCKET_PATH}")

        previous_packet = {}

        while not service_helper.time_to_stop():
            # Get values to pass to emulator
            # These states are validated, error checked and include fallback
            pendant_state_dict = controller.get_state_table().get_gse_states()

            change_in_pendant_data = previous_packet != pendant_state_dict
            previous_packet = pendant_state_dict

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
        frontend_pub_socket.close()
        slogger.debug("Packet sender closed socket")
        slogger.debug(f"Packet sender closing context (<{LINGER_TIME_MS}ms)")
        context.term()
        slogger.debug("Packet sender thread resources cleaned up")
        slogger.debug("Cleaning up controller")
        controller.cleanup()
        slogger.debug("Cleaned up controller")


def main():
    device_emulator.MockPacket.initialize_settings(
        config.get_config()["emulation"]
    )
    slogger.debug("Starting pendant emulator")

    # global packet_thread
    # packet_thread = threading.Thread(target=send_packet)
    # packet_thread.start()
    send_packet()


if __name__ == "__main__":
    main()
