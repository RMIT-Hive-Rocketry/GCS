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
import backend.device_emulator as device_emulator
import backend.includes_python.service_helper as service_helper
from backend.includes_python.devices.control_device import ControlDevice
from backend.includes_python.devices.state_table import StateTable
import config.config as config
from typing import List, Dict, Tuple, Type

try:
    from gpiozero import Button
except (ImportError, RuntimeError):
    slogger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    slogger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    slogger.error(
        "gpiozero not found, this library is only available on Raspberry Pi devices."
    )
    slogger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    slogger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    class Button:
        def __init__(self, pin, pull_up=False):
            self.pin = pin

        @property
        def is_pressed(self):
            return False



class RPI_GPIO_Device(ControlDevice):
    """Parent class for GPIO devices on Raspberry Pi."""

    # MAPPING FROM DB15 PINS
    # From https://github.com/RMIT-Hive-Rocketry/GCS-2026/blob/main/docs/assets/pendant_wiring.png
    # PIN1 -> POWER (5V)?
    # DB_PIN_GPIO_0 -> (SYS_ACTIVE)
    # DB_PIN_GPIO_1 -> (FILL_SELECTED)
    # DB_PIN_GPIO_2 -> (IGNITION_SELECTED)
    # DB_PIN_GPIO_3 -> (IGNITION_MOMENT_ACTIVE)
    # DB_PIN_GPIO_4 -> (N2O_ACTIVE)
    # DB_PIN_GPIO_5 -> (NEUTRAL_ACTIVE) *currently unwired*
    # DB_PIN_GPIO_6 -> (O2_MOMENT_ACTIVE)
    # DB_PIN_GPIO_7 -> (PURGE_ACTIVE)
    # PIN9 -> GND

    # What GPIO ports represent the logical input
    PIN_MAP = {
        4: "SYS_ON",
        17: "FILL_SELECTED",
        27: "IGNITION_SELECTED",
        22: "IGNITION_MOMENT_ACTIVE",
        10: "N2O_ACTIVE",
        9: "NEUTRAL_ACTIVE",
        11: "O2_MOMENT_ACTIVE",
        5: "PURGE_ACTIVE",
    }

    def _setup_device(self):
        self.buttons = {
            pin: Button(pin, pull_up=False, bounce_time=0.05)
            for pin in RPI_GPIO_Device.PIN_MAP
        }

    def __init__(self):
        super().__init__()

    def _update_state_table(self):
        """Updates instance attributes and returns a dictionary of the current states."""
        for pin, attr in RPI_GPIO_Device.PIN_MAP.items():
            setattr(self, attr, self.buttons[pin].is_pressed)
        states = {
            attr: getattr(self, attr)
            for attr in RPI_GPIO_Device.PIN_MAP.values()
        }
        # Temporary fix for neutral state which isn't wired
        states["NEUTRAL_ACTIVE"] = (
            self.SYS_ON and not self.N2O_ACTIVE and not self.PURGE_ACTIVE
        )
        self.state_table = StateTable(**states)


_TA320_BUTTON_NAME_ID_MAP: Dict[str, int] = {
    "SYS_ON": 16,  # thrust
    # "ESTOP":                    idk
    "FILL_SELECTED": 1,  # top trigger
    "IGNITION_SELECTED": 0,  # bottom trigger
    "N2O_ACTIVE": 7,  # bottom left button on right side
    "PURGE_ACTIVE": 2,  # spherical button
    "O2_MOMENT_ACTIVE": 6,  # top left button on right side
    "IGNITION_MOMENT_ACTIVE": 3,  # red button
}


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
