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
import config.config as config
import threading
from typing import List, Dict, Tuple, Type
from abc import ABC, abstractmethod

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


# ==============================
# ==============================
# TODO: add event based GPIO changes here, don't run polls.
# ==============================
# ==============================


class StateTable:
    """
    Stores the states (argument) for the GSE to GCS packet. bonza cunt
    """

    FALLBACK_DICT = {
        "SYS_ON": False,
        "FILL_SELECTED": False,
        "IGNITION_SELECTED": False,
        "N2O_ACTIVE": False,
        "NEUTRAL_ACTIVE": False,
        "PURGE_ACTIVE": False,
        "O2_MOMENT_ACTIVE": False,
        "IGNITION_MOMENT_ACTIVE": False,
    }

    @staticmethod
    def _bool_table_str(printable_dict: dict) -> str:
        MAX_KEY_LEN = max(len(str(k)) for k in printable_dict)
        output = ""
        for k, v in printable_dict.items():
            assert isinstance(v, bool)
            symbol = "[X]" if v else "[ ]"
            output += f"{k:<{MAX_KEY_LEN}} : {symbol}\n"
        return output

    def __str__(self):
        mock_states = self.get_states_dict()
        return StateTable._bool_table_str(mock_states)

    def __repr__(self):
        """Debug print statement"""
        debug_attributes = {
            "SYS_ON": self.SYS_ON,
            "FILL_SELECTED": self.FILL_SELECTED,
            "IGNITION_SELECTED": self.IGNITION_SELECTED,
            "N2O_ACTIVE": self.N2O_ACTIVE,
            "NEUTRAL_ACTIVE": self.NEUTRAL_ACTIVE,
            "PURGE_ACTIVE": self.PURGE_ACTIVE,
            "O2_MOMENT_ACTIVE": self.O2_MOMENT_ACTIVE,
            "IGNITION_MOMENT_ACTIVE": self.IGNITION_MOMENT_ACTIVE,
        }
        # Get string of outputs
        output = StateTable._bool_table_str(debug_attributes)
        # Get string if calculated packet states
        output += "\n"
        output += self.__str__()
        return output

    def __eq__(self, other):
        if not isinstance(other, StateTable):
            return NotImplemented
        return self.get_states_dict() == other.get_states_dict()

    def __ne__(self, other):
        return not self == other

    def __init__(
        self,
        SYS_ON: bool = True,
        FILL_SELECTED: bool = True,
        IGNITION_SELECTED: bool = True,
        N2O_ACTIVE: bool = True,
        NEUTRAL_ACTIVE: bool = True,
        PURGE_ACTIVE: bool = True,
        O2_MOMENT_ACTIVE: bool = True,
        IGNITION_MOMENT_ACTIVE: bool = True,
        ESTOP: bool = False,
    ):
        self.SYS_ON = SYS_ON
        self.FILL_SELECTED = FILL_SELECTED
        self.IGNITION_SELECTED = IGNITION_SELECTED
        self.N2O_ACTIVE = N2O_ACTIVE
        self.NEUTRAL_ACTIVE = NEUTRAL_ACTIVE
        self.PURGE_ACTIVE = PURGE_ACTIVE
        self.O2_MOMENT_ACTIVE = O2_MOMENT_ACTIVE
        self.IGNITION_MOMENT_ACTIVE = IGNITION_MOMENT_ACTIVE
        self.ESTOP = ESTOP

    def get_states_dict(self) -> dict:
        """returns argument dictionary for use in GCS to GSE packet"""
        # You should also check these states electronically where applicable
        # fmt: off
        states = {
            "MANUAL_PURGE": self.SYS_ON and self.FILL_SELECTED and self.PURGE_ACTIVE,
            "O2_FILL_ACTIVATE": self.SYS_ON and self.IGNITION_SELECTED and self.O2_MOMENT_ACTIVE,
            "SELECTOR_SWITCH_NEUTRAL_POSITION": self.SYS_ON and self.FILL_SELECTED and self.NEUTRAL_ACTIVE,
            "N2O_FILL_ACTIVATE": self.SYS_ON and self.FILL_SELECTED and self.N2O_ACTIVE,
            "IGNITION_FIRE": self.SYS_ON and self.IGNITION_SELECTED and self.IGNITION_MOMENT_ACTIVE,
            "IGNITION_SELECTED": self.SYS_ON and self.IGNITION_SELECTED,
            "GAS_FILL_SELECTED": self.SYS_ON and self.FILL_SELECTED,
            "SYSTEM_ACTIVATE": self.SYS_ON,
        }
        # fmt: on

        # Type and range validation
        if (
            any(not isinstance(x, bool) for x in states.values())
            or len(states) != 8
        ):
            slogger.error(f"Missing/invalid states: {states}")
            return StateTable.get_fallback_table()

        # Nonsensical states that should not exist. GSE will complain if any true
        nonsensical_conditions = {
            "purge and fill": states["MANUAL_PURGE"]
            and states["O2_FILL_ACTIVATE"],
            "purge on neutral": states["MANUAL_PURGE"]
            and states["SELECTOR_SWITCH_NEUTRAL_POSITION"],
            # states["MANUAL_PURGE"] and states["SELECTOR_SWITCH_NEUTRAL_POSITION"]
            # add more. please do this automatically
        }

        for k, v in nonsensical_conditions.items():
            if v:
                slogger.warning(f"Impossible condition detected: {k}")
                states = StateTable.FALLBACK_DICT

        return states

    def get_fallback_table() -> dict:
        """Return an instance of StateTable which is safe"""
        return StateTable(**StateTable.FALLBACK_DICT)


class ControlDevice(ABC):
    def __init__(self):
        # DONT instanciate a ControlDevice manually
        # Use the get_control_device() funciton
        self._setup_device()
        # Set default fallback state to send whist waiting for inputs
        self.state_table = StateTable.get_fallback_table()

    @abstractmethod
    def _setup_device(self):
        """Setup the control device"""
        pass

    @abstractmethod
    def _update_state_table(self) -> None:
        """Updates state table with new values"""
        pass

    def get_state_table(self) -> StateTable:
        """Updates and gets the current states from the control device."""
        try:
            self._update_state_table()
        except Exception as e:
            slogger.warning(f"Failed to update pendant states : {e}")

        if not self.state_table:
            slogger.warning(
                "No inputs received from control device, using fallback state"
            )
            self.state_table = StateTable.get_fallback_table()
        return self.state_table

    def get_states_dict(self) -> dict:
        state_table = self.get_state_table()
        return state_table.get_states_dict()

    def cleanup(self):
        """Code to run after controller is no longer needed."""
        pass


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


class HID_Button:
    MAX_SAFETY_COUNT: int = 10
    USEFUL_BYTE_OFFSET: int = 5
    MIN_TIME_BETWEEN_STATE_CHANGE: float = 0.05
    # percentage of the last MAX_SAFETY_COUNT inputs which need to be on for a press to register
    SAFETY_FACTOR: float = 0.5

    byte: int  # [0, 1]
    bit: int  # [0, 7]
    bitmask: int

    safety_count: int = 0
    time_of_last_state_change: float
    button_is_pressed: bool = False

    def __init__(self, byte, bit):
        self.byte = byte
        self.bit = bit
        self.bitmask = 1 << bit
        self.time_of_last_state_change = time.time()

    def _try_update_state(self, new_state: bool):
        if new_state:
            self.safety_count = min(
                self.safety_count + 1, HID_Button.MAX_SAFETY_COUNT
            )
        else:
            self.safety_count = max(self.safety_count - 1, 0)

        time_since_last_state_change = (
            time.time() - self.time_of_last_state_change
        )

        if (
            time_since_last_state_change
            < HID_Button.MIN_TIME_BETWEEN_STATE_CHANGE
        ):
            return

        safety_check = (
            self.safety_count / HID_Button.MAX_SAFETY_COUNT
            > HID_Button.SAFETY_FACTOR
        )

        if safety_check and not self.button_is_pressed:
            self.button_is_pressed = True
            self.time_of_last_state_change = time.time()
        elif not safety_check and self.button_is_pressed:
            self.button_is_pressed = False
            self.time_of_last_state_change = time.time()

    def update_state(self, hid_bytes: List[int]) -> None:
        if len(hid_bytes) < 7:
            slogger.error(
                f"hid_bytes is too small, expected 7, got {len(hid_bytes)}"
            )
            return

        byte_index = HID_Button.USEFUL_BYTE_OFFSET + self.byte
        hid_byte = hid_bytes[byte_index]

        self._try_update_state(hid_byte & self.bitmask)

    def is_pressed(self) -> bool:
        return self.button_is_pressed


class HID_Device(ControlDevice):
    """Parent class for HID devices on Raspberry Pi."""

    """
    name of input i was given to what i think its supposed to be
        "system_key":           SYS_ON
        "e_stop":               ESTOP - NOT USED FOR NOW
        "sys_select_pos_up":    FILL_SELECTED
        "sys_select_pos_down":  IGNITION_SELECTED
        "fill_switch_pos_up":   N2O_ACTIVE
        "fill_switch_pos_down": PURGE_ACTIVE
        "o2_fill_button":       O2_MOMENT_ACTIVE
        "ignition_button":      IGNITION_MOMENT_ACTIVE
    """

    HID_VENDOR_ID = 0x0079
    HID_PRODUCT_ID = 0x0006

    # THESE ARE PROB WRONG, wiring has changed since i got these
    # name: (byte, bit)
    BITMAP: Dict[str, Tuple[int, int]] = {
        "SYS_ON": (1, 5),
        # "ESTOP": (1, 6),
        "FILL_SELECTED": (0, 2),
        "IGNITION_SELECTED": (0, 1),
        "N2O_ACTIVE": (0, 0),
        "PURGE_ACTIVE": (1, 7),
        "O2_MOMENT_ACTIVE": (1, 4),
        "IGNITION_MOMENT_ACTIVE": (1, 3),
    }

    buttons: Dict[str, HID_Button]

    device: hid.Device
    device_is_connected: bool = False

    def _try_connect_device(self):
        try:
            self.device = hid.Device()
            self.device.open(
                HID_Device.HID_VENDOR_ID, HID_Device.HID_PRODUCT_ID
            )
            self.device_is_connected = True
        except IOError as e:
            # TODO: stop spamming the slogger
            slogger.warning(f"Control Pendant is not connected, error: `{e}`")
            self.device_is_connected = False

    def _setup_device(self):
        self._try_connect_device()

        for btn_name in HID_Device.BITMAP:
            self.buttons[btn_name] = HID_Button(*HID_Device.BITMAP[btn_name])

    def __init__(self):
        super().__init__()
        self.buttons = {}
        slogger.warning(
            "HID_Device is not tested, dont use it untill lab testing has been done"
        )

    def _update_state_table(self):
        """Updates instance attributes"""
        try:
            if not self.device_is_connected:
                self._try_connect_device()
            if not self.device_is_connected:
                return None

            bytes = self.device.read(9999)

            for _, btn in self.buttons.items():
                btn.update_state(bytes)

            states: Dict[str:bool] = {
                btn_name: btn.is_pressed()
                for btn_name, btn in self.buttons.items()
            }
            # Temporary fix for neutral state which isn't wired
            states["NEUTRAL_ACTIVE"] = (
                states["SYS_ON"]
                and not states["N2O_ACTIVE"]
                and not states["PURGE_ACTIVE"]
            )

            self.state_table = StateTable(**states)

        except IOError:
            self.device_is_connected = False
            self.state_table = StateTable.get_fallback_table()

    def cleanup(self):
        self.device.close()


class Pygame_Button:
    MIN_TIME_BETWEEN_STATE_CHANGE: float = 0.05

    time_of_last_state_change: float
    button_is_pressed: bool = False

    def __init__(self):
        self.time_of_last_state_change = time.time()

    def _try_update_state(self, new_state: bool):
        time_since_last_state_change = (
            time.time() - self.time_of_last_state_change
        )

        if (
            time_since_last_state_change
            < Pygame_Button.MIN_TIME_BETWEEN_STATE_CHANGE
        ):
            return

        if new_state and not self.button_is_pressed:
            self.button_is_pressed = True
            self.time_of_last_state_change = time.time()
        elif not new_state and self.button_is_pressed:
            self.button_is_pressed = False
            self.time_of_last_state_change = time.time()

    # will update state if safe to do so
    def update_state(self, new_state: bool):
        self._try_update_state(new_state)

    def is_pressed(self):
        return self.button_is_pressed


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


class Pygame_Device(ControlDevice):
    """
    Parent class for Pygame devices on Raspberry Pi.
    Handles all pygame setup and shutdown
    """

    BUTTON_NAME_ID_MAP: Dict[str, int] = {
        "SYS_ON": 0,
        "ESTOP": 5,
        "FILL_SELECTED": 6,
        "IGNITION_SELECTED": 4,
        "N2O_ACTIVE": 8,
        "PURGE_ACTIVE": 3,
        "O2_MOMENT_ACTIVE": 1,
        "IGNITION_MOMENT_ACTIVE": 2,
    }

    BUTTON_ID_NAME_MAP: Dict[int, str] = {
        v: k for k, v in BUTTON_NAME_ID_MAP.items()
    }

    buttons: Dict[str, Pygame_Button]

    CONTROLLER_NAME: str = "DragonRise Inc. Generic USB Joystick"

    joystick: pygame.joystick.JoystickType | None = None
    joystick_id: int
    is_connected: bool = False

    def __init__(self):
        super().__init__()
        self.buttons = {}
        for but_name, _ in Pygame_Device.BUTTON_NAME_ID_MAP.items():
            self.buttons[but_name] = Pygame_Button()

    def _try_connect_device(self):
        # Attempt controller connection
        if pygame.joystick.get_count() == 0:
            # slogger.warning("No Controllers Connected")
            return

        # Don't re-attempt connection if device is already connected
        if Pygame_Device.is_connected:
            return

        # this should only be called when these are junk (controller disconnected, startup etc)
        # Pygame_Device.is_connected = False
        # Pygame_Device.joystick = None
        found_names = ""

        for i in range(pygame.joystick.get_count()):
            jstk = pygame.joystick.Joystick(i)
            jstk.init()
            found_names += jstk.get_name()
            found_names += ", "
            if jstk.get_name() == Pygame_Device.CONTROLLER_NAME:
                Pygame_Device.is_connected = True
                Pygame_Device.joystick = jstk
                Pygame_Device.joystick_id = jstk.get_instance_id()

                slogger.info(
                    f"Controller initialized: {Pygame_Device.joystick.get_name()}"
                )
                break

        if not Pygame_Device.is_connected:
            # slogger.warning(
            #     "Did not find controller '"
            #     + Pygame_Device.CONTROLLER_NAME
            #     + "'"
            #     + " found controllers '"
            #     + found_names
            #     + "'"
            # )
            return

    def _setup_device(self):
        pygame.init()
        # pygame.mixer.quit() # https: // stackoverflow.com/a/50552161/14141223
        pygame.joystick.init()
        self._try_connect_device()

    def _update_state_table(self):
        """Updates instance attributes"""
        pygame.event.pump()  # seg fault on mac if i dont do this

        if not Pygame_Device.is_connected:
            self._try_connect_device()

        # check for disconection
        events: List[pygame.event.Event] = pygame.event.get()
        for event in events:
            if (
                event.type == pygame.JOYDEVICEREMOVED
                and event.instance_id == Pygame_Device.joystick_id
            ):
                Pygame_Device.joystick = None
                Pygame_Device.is_connected = False
                Pygame_Device.joystick_id = 0
                slogger.error("Pendnat Disconnected")

        if Pygame_Device.is_connected and Pygame_Device.joystick is not None:
            # polling events on mac gave me segfaults
            for btn_name, btn_id in Pygame_Device.BUTTON_NAME_ID_MAP.items():
                try:
                    pressed = bool(Pygame_Device.joystick.get_button(btn_id))
                except Exception:
                    # Don't automatically disconnect device when an unexpected button is pressed
                    # Since the joystick sends noisy/useless data, it causes it to reconnect endlessly
                    pressed = False
                self.buttons[btn_name].update_state(pressed)

            states = {
                btn_name: btn.is_pressed()
                for btn_name, btn in self.buttons.items()
            }

            # Temporary fix for neutral state which isn't wired
            states["SYS_ON"] = not states["ESTOP"]
            states["NEUTRAL_ACTIVE"] = (
                states["SYS_ON"]
                and not states["N2O_ACTIVE"]
                and not states["PURGE_ACTIVE"]
            )
            self.state_table = StateTable(**states)
        else:
            self.state_table = StateTable.get_fallback_table()

        """
        states = {}
        if Pygame_Device.is_connected:
            states = {
                btn_name: btn.is_pressed() for btn_name, btn in self.buttons.items()
            }
        else:
            states = StateTable.FALLBACK_DICT.copy()
        """

    def cleanup(self):
        """Internal cleaup code"""
        slogger.info("Quitting pygame...")
        pygame.quit()
        slogger.info("Pygame killed. Done...")


class Emulated_Device(Pygame_Device):
    """
    Emulated device class, FOR TESTING ONLY
    Based on the Pygame_Device class, even though it doesn't actually use Pygame
    """

    BUTTON_NAME_ID_MAP: Dict[str, int] = {
        "SYS_ON": 0,
        "ESTOP": 5,
        "FILL_SELECTED": 6,
        "IGNITION_SELECTED": 4,
        "N2O_ACTIVE": 8,
        "PURGE_ACTIVE": 3,
        "O2_MOMENT_ACTIVE": 1,
        "IGNITION_MOMENT_ACTIVE": 2,
    }

    BUTTON_ID_NAME_MAP: Dict[int, str] = {
        v: k for k, v in BUTTON_NAME_ID_MAP.items()
    }

    BUTTON_SEQUENCE = [
        [],
        ["FILL_SELECTED"],
        ["FILL_SELECTED", "N2O_ACTIVE"],
        ["FILL_SELECTED"],
        ["FILL_SELECTED", "PURGE_ACTIVE"],
        ["FILL_SELECTED"],
        [],
        ["IGNITION_SELECTED"],
        ["IGNITION_SELECTED", "O2_MOMENT_ACTIVE"],
        ["IGNITION_SELECTED"],
        ["IGNITION_SELECTED", "IGNITION_MOMENT_ACTIVE"],
        ["IGNITION_SELECTED"],
        ["IGNITION_SELECTED", "O2_MOMENT_ACTIVE", "IGNITION_MOMENT_ACTIVE"],
        ["IGNITION_SELECTED"],
        [],
    ]

    CONTROLLER_NAME: str = "EMULATED USB CONTROLLER - FOR TESTING ONLY"
    is_connected: bool = False

    def __init__(self):
        super().__init__()
        self.buttons = {}

    def _try_connect_device(self):
        # This device never has connection issues
        Emulated_Device.is_connected = True
        slogger.info(
            f"Controller initialized: {Emulated_Device.CONTROLLER_NAME}"
        )

    def _setup_device(self):
        pygame.init()
        self._try_connect_device()

    def _update_state_table(self):
        """Updates instance attributes"""
        pygame.event.pump()

        if Emulated_Device.is_connected:

            # Loop through states and update them
            seconds = int(time.time())
            current_buttons = Emulated_Device.BUTTON_SEQUENCE[
                seconds % len(Emulated_Device.BUTTON_SEQUENCE)
            ]

            for btn_name, btn_id in Emulated_Device.BUTTON_NAME_ID_MAP.items():
                pressed = btn_name in current_buttons
                self.buttons[btn_name] = pressed

            states = {btn_name: btn for btn_name, btn in self.buttons.items()}

            # Temporary fix for neutral state which isn't wired
            states["SYS_ON"] = not states["ESTOP"]
            states["NEUTRAL_ACTIVE"] = (
                states["SYS_ON"]
                and not states["N2O_ACTIVE"]
                and not states["PURGE_ACTIVE"]
            )
            self.state_table = StateTable(**states)
        else:
            self.state_table = StateTable.get_fallback_table()

    def cleanup(self):
        """Internal cleaup code"""
        slogger.info("Quitting pygame...")
        pygame.quit()
        slogger.info("Pygame killed. Done...")

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
    TIME_BETWEEN_GSE_PACKETS_S = 0.1 # so server doesnt think we died
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
        gse_push_socket.setsockopt(zmq.SNDHWM, 1)  # Limit send buffer to 1 message
        gse_push_socket.connect(f"ipc://{GSE_SOCKET_PATH}")

        frontend_push_socket = context.socket(zmq.PUSH)
        frontend_push_socket.setsockopt(zmq.LINGER, LINGER_TIME_MS)
        frontend_push_socket.setsockopt(zmq.SNDHWM, 1)  # Limit send buffer to 1 message
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
            state_command = device_emulator.GCStoGSEStateCMD(**pendant_state_dict)

            time_since_last_gse_packet = time.time() - time_of_last_gse_packet
            time_since_last_frontend_packet = time.time() - time_of_last_frontend_packet

            change_in_pendant_data = previous_packet != pendant_state_dict

            previous_packet = pendant_state_dict

            # NEVER SEND PACKET FROM THE EMULATED_DEVICE TO THE SERVER
            not_emulated_device = CONTROL_TYPE != "emulated_device"
            time_check_gse = time_since_last_gse_packet > TIME_BETWEEN_GSE_PACKETS_S

            if not_emulated_device and (time_check_gse or change_in_pendant_data):
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

            time_check_frontend = time_since_last_frontend_packet > TIME_BETWEEN_FRONTEND_PACKETS_S
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
        config.get_config()["emulation"]
    )
    slogger.debug("Starting pendant daemon")

    # global packet_thread
    # packet_thread = threading.Thread(target=send_packet)
    # packet_thread.start()
    send_packet()


if __name__ == "__main__":
    main()
