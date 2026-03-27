import backend.includes_python.process_logging as slogger
import zmq
import os
import time
import backend.device_emulator as device_emulator
import backend.includes_python.service_helper as service_helper
from backend.includes_python.timers import RepeatingTimer
from backend.includes_python.devices.control_device_manager import ControlDeviceManager
from backend.includes_python.devices.control_device import ControlDevice

import config.config as config
from typing import Type

# Wait LINGER_TIME_MS before giving up on push request
LINGER_TIME_MS = 300

# path to the socket that gets forwarded to GSE in the c++ server
GSE_SOCKET_PATH = os.path.abspath(
    os.path.join(os.path.sep, "tmp", "gcs_rocket_pendant_pull.sock")
)

# path to the socket read by frontend api
FRONTEND_SOCKET_PATH = os.path.abspath(
    os.path.join(os.path.sep, "tmp", "gcs_pendant_frontend_pull.sock")
)

# "rpi_gpio_device": None,
# "hid_device": None,
# "pygame_device": None,
# "emulated_device": None,

def get_control_device():
    manager = ControlDeviceManager()

    #TODO: make these match pep-8 CapWords naming convention instead of Snake_Case
    
    def rpi_import() -> Type[ControlDevice]:
        from backend.includes_python.devices.rpi_gpio_device import RPI_GPIO_Device
        return RPI_GPIO_Device

    def hid_import() -> Type[ControlDevice]:
        from backend.includes_python.devices.hid_device import HID_Device
        return HID_Device

    def pygame_import() -> Type[ControlDevice]:
        from backend.includes_python.devices.pygame_device import Pygame_Device
        return Pygame_Device

    manager.add_managed_device(
        name = "rpi_gpio_device",
        import_func = rpi_import
    )

    manager.add_managed_device(
        name = "hid_device",
        import_func = hid_import
    )

    manager.add_managed_device(
        name = "pygame_device",
        import_func = pygame_import
    )

    return manager.get_control_device()

def send_packet():
    context = zmq.Context()

    gse_packet_send_timer = RepeatingTimer(0.05)
    frontend_packet_send_timer = RepeatingTimer(0.5)
    gse_complain_timer = RepeatingTimer(5)
    frontend_complain_timer = RepeatingTimer(5)

    controller = get_control_device()

    try:
        gse_push_socket = context.socket(zmq.PUSH)
        gse_push_socket.setsockopt(zmq.LINGER, LINGER_TIME_MS)
        gse_push_socket.setsockopt(
            zmq.SNDHWM, 1
        )  # Limit send buffer to 1 message
        gse_push_socket.connect(f"ipc://{GSE_SOCKET_PATH}")

        frontend_push_socket = context.socket(zmq.PUSH)
        frontend_push_socket.setsockopt(zmq.LINGER, LINGER_TIME_MS)
        frontend_push_socket.setsockopt(
            zmq.SNDHWM, 1
        )  # Limit send buffer to 1 message
        frontend_push_socket.connect(f"ipc://{FRONTEND_SOCKET_PATH}")

        previous_packet = {}

        while not service_helper.time_to_stop():
            # Get values to pass to emulator
            # These states are validated, error checked and include fallback
            pendant_state_dict = controller.get_states_dict()
            state_command = device_emulator.GCStoGSEStateCMD(
                **pendant_state_dict
            )

            change_in_pendant_data = previous_packet != pendant_state_dict
            previous_packet = pendant_state_dict

            # NEVER SEND PACKET FROM THE EMULATED_DEVICE TO THE SERVER
            if gse_packet_send_timer.time_has_passed() or change_in_pendant_data:
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

            if frontend_packet_send_timer.time_has_passed() or change_in_pendant_data:
                # send to frontend api
                try:
                    frontend_push_socket.send_json(
                        pendant_state_dict,
                        flags=zmq.NOBLOCK,
                    )
                except zmq.ZMQError:
                    # Queue is likely full
                    if frontend_complain_timer.time_has_passed():
                        slogger.warning(
                            "Frontend ZMQ Push socket is full. Cannot send data until it is emptied in server."
                        )

            # No need to go full blast.
            time.sleep(0.05)
    finally:
        slogger.debug("Packet sender closing socket")
        gse_push_socket.close()
        frontend_push_socket.close()
        slogger.debug("Packet sender closed socket")
        slogger.debug(f"Packet sender closing context (<{LINGER_TIME_MS}ms)")
        context.term()
        slogger.debug("Packet sender thread resources cleaned up")
        slogger.debug("Cleaning up controller")
        controller.cleanup()
        slogger.debug("Cleaned up controller")


def main():
    device_emulator.MockPacket.initialize_settings(
        config.get_config()['emulation'])
    slogger.debug("Starting pendant emulator")

    # global packet_thread
    # packet_thread = threading.Thread(target=send_packet)
    # packet_thread.start()
    send_packet()


if __name__ == "__main__":
    main()
