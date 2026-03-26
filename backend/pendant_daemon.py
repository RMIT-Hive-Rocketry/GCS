import backend.includes_python.process_logging as slogger
import zmq
import os
import time
import backend.device_emulator as device_emulator
import backend.includes_python.service_helper as service_helper
from backend.includes_python.devices.control_device import ControlDevice
import config.config as config
from typing import Dict, Type

instances: Dict[str, None | ControlDevice] = {
    "rpi_gpio_device": None,
    "hid_device": None,
    "pygame_device": None,
    "emulated_device": None,
}

def get_control_device(key: str) -> ControlDevice:
    # instead of making each control device a singleton we can add logic here to only instanciate it once
    global instances

    str_to_device: Dict[str, Type[ControlDevice]] = {
        "rpi_gpio_device": RPI_GPIO_Device,
        "hid_device": HID_Device,
        "pygame_device": Pygame_Device,
        "emulated_device": Emulated_Device,
    }

    key = key.lower().strip()

    if key not in instances:
        error_str = f"Control Device `{key}` not recognised, check that `controller` is set correctly in config.ini"
        slogger.error(error_str)
        raise ValueError(error_str)

    if instances[key] is None:
        instances[key] = str_to_device[key]()

    return instances[key]


def send_packet():
    CONFIG = config.get_config()

    CONTROL_TYPE = CONFIG["hardware"]["controller"]

    context = zmq.Context()

    # Wait LINGER_TIME_MS before giving up on push request
    LINGER_TIME_MS = 300

    # send packets on an interval of TIME_BETWEEN_PACKETS and also when there is a change
    TIME_BETWEEN_GSE_PACKETS_S = 0.1  # so server doesnt think we died
    TIME_BETWEEN_FRONTEND_PACKETS_S = 1.0

    try:
        controller: ControlDevice = get_control_device(CONTROL_TYPE)

        # path to the socket that gets forwarded to GSE in the c++ server
        GSE_SOCKET_PATH = os.path.abspath(
            os.path.join(os.path.sep, "tmp", "gcs_rocket_pendant_pull.sock")
        )

        # path to the socket read by frontend api
        FRONTEND_SOCKET_PATH = os.path.abspath(
            os.path.join(os.path.sep, "tmp", "gcs_pendant_frontend_pull.sock")
        )

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

        time_of_last_gse_packet = 0
        time_of_last_frontend_packet = 0
        previous_packet = {}

        # wait for other services to open
        time.sleep(10)

        while not service_helper.time_to_stop():
            # Get values to pass to emulator
            # These states are validated, error checked and include fallback
            pendant_state_dict = controller.get_states_dict()
            state_command = device_emulator.GCStoGSEStateCMD(
                **pendant_state_dict
            )

            time_since_last_gse_packet = time.time() - time_of_last_gse_packet
            time_since_last_frontend_packet = (
                time.time() - time_of_last_frontend_packet
            )

            change_in_pendant_data = previous_packet != pendant_state_dict

            previous_packet = pendant_state_dict

            # NEVER SEND PACKET FROM THE EMULATED_DEVICE TO THE SERVER
            not_emulated_device = CONTROL_TYPE != "emulated_device"
            time_check_gse = (
                time_since_last_gse_packet > TIME_BETWEEN_GSE_PACKETS_S
            )

            if not_emulated_device and (
                time_check_gse or change_in_pendant_data
            ):
                # send to c++ server to forward to GSE
                try:
                    gse_push_socket.send(
                        state_command.get_payload_bytes(EXTERNAL=True),
                        flags=zmq.NOBLOCK,
                    )
                except zmq.ZMQError:
                    # Queue is likely full
                    slogger.warning(
                        "Server ZMQ Push socket is full. Cannot send data until it is emptied in server."
                    )
                    time.sleep(1)

                time_of_last_gse_packet = time.time()

            time_check_frontend = (
                time_since_last_frontend_packet
                > TIME_BETWEEN_FRONTEND_PACKETS_S
            )
            if time_check_frontend or change_in_pendant_data:
                # send to frontend api
                try:
                    frontend_push_socket.send_json(
                        pendant_state_dict,
                        flags=zmq.NOBLOCK,
                    )
                except zmq.ZMQError:
                    # Queue is likely full
                    slogger.warning(
                        "Frontend ZMQ Push socket is full. Cannot send data until it is emptied in server."
                    )
                    time.sleep(0.25)
                time_of_last_frontend_packet = time.time()

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
