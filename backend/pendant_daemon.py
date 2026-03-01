'''
export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH
'''

import backend.includes_python.process_logging as slogger

try:
    import hid
except (ImportError, RuntimeError) as e:
    '''
    if the hid module fails to import and you dont want to use a hid controller, then no harm so just warn in slogger
    if you want the hid device (controller = rpi_gpio_device)
    '''
    error_message = "This should not have run, make sure you set controller = rpi_gpio_device or pygame_device (config.ini) or check your hid install is correct"
    slogger.error(f"hid is not correctly installed: {e}. This is okay if your using rpi_gpio_device or pygame_device (check config.ini)")
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
from typing import List, Dict, Tuple
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
        def __init__(self, pin, pull_up=False): self.pin = pin
        @property
        def is_pressed(self): return False


# ==============================
# ==============================
# TODO: add event based GPIO changes here, don't run polls.
# ==============================
# ==============================



class StateTable():
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
            symbol = '[X]' if v else '[ ]'
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
        output += '\n'
        output += self.__str__()
        return output

    def __eq__(self, other):
        if not isinstance(other, StateTable):
            return NotImplemented
        return self.get_states_dict() == other.get_states_dict()

    def __ne__(self, other):
        return not self == other

    def __init__(self,
                 SYS_ON: bool = True,
                 FILL_SELECTED: bool = True,
                 IGNITION_SELECTED: bool = True,
                 N2O_ACTIVE: bool = True,
                 NEUTRAL_ACTIVE: bool = True,
                 PURGE_ACTIVE: bool = True,
                 O2_MOMENT_ACTIVE: bool = True,
                 IGNITION_MOMENT_ACTIVE: bool = True,
                 ):
        self.SYS_ON = SYS_ON
        self.FILL_SELECTED = FILL_SELECTED
        self.IGNITION_SELECTED = IGNITION_SELECTED
        self.N2O_ACTIVE = N2O_ACTIVE
        self.NEUTRAL_ACTIVE = NEUTRAL_ACTIVE
        self.PURGE_ACTIVE = PURGE_ACTIVE
        self.O2_MOMENT_ACTIVE = O2_MOMENT_ACTIVE
        self.IGNITION_MOMENT_ACTIVE = IGNITION_MOMENT_ACTIVE

    def get_states_dict(self) -> dict:
        """returns argument dictionary for use in GCS to GSE packet
        """
        # You should also check these states electronically where applicable
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

        # Type and range validation
        if any(not isinstance(x, bool) for x in states.values()) or len(states) != 8:
            slogger.error(f"Missing/invalid states: {states}")
            return StateTable.get_fallback_table()

        # Nonsensical states that should not exist. GSE will complain if any true
        nonsensical_conditions = {
            "purge and fill": states["MANUAL_PURGE"] and states["O2_FILL_ACTIVATE"],
            "purge on neutral": states["MANUAL_PURGE"] and states["SELECTOR_SWITCH_NEUTRAL_POSITION"],
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
        except Exception:
            slogger.warning("Failed to update pendant states")
        if not self.state_table:
            slogger.warning(
                "No inputs received from control device, using fallback state")
            state_table = StateTable.get_fallback_table()
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
            pin: Button(pin, pull_up=False, bounce_time=0.05) for pin in RPI_GPIO_Device.PIN_MAP
        }

    def __init__(self):
        super().__init__()

    def _update_state_table(self):
        """Updates instance attributes and returns a dictionary of the current states."""
        for pin, attr in RPI_GPIO_Device.PIN_MAP.items():
            setattr(self, attr, self.buttons[pin].is_pressed)
        states = {
            attr: getattr(self, attr) for attr in RPI_GPIO_Device.PIN_MAP.values()
        }
        # Temporary fix for neutral state which isn't wired
        self.NEUTRAL_ACTIVE = not self.N2O_ACTIVE and not self.PURGE_ACTIVE
        self.state_table = StateTable(**states)


class HID_Button:
    MAX_SAFETY_COUNT: int = 10
    USEFUL_BYTE_OFFSET: int = 5
    MIN_TIME_BETWEEN_STATE_CHANGE: float = 0.05
    SAFETY_FACTOR: float = 0.5 # percentage of the last MAX_SAFETY_COUNT inputs which need to be on for a press to register

    byte: int # [0, 1]
    bit: int # [0, 7]
    bitmask: int
    
    safety_count: int = 0
    time_of_last_state_change: float
    button_is_pressed: bool = False
    
    def __init__(self, byte, bit):
        self.byte = byte
        self.bit = bit
        self.bitmask = 1 << bit
        self.time_of_last_state_change = time.time()


    def update_state(self, hid_bytes: List[int]) -> None:
        if len(hid_bytes) < 7:
            slogger.error(f"hid_bytes is too small, expected 7, got {len(hid_bytes)}")
            return

        byte_index = HID_Button.USEFUL_BYTE_OFFSET + self.byte
        hid_byte = hid_bytes[byte_index]

        if hid_byte & self.bitmask:
            self.safety_count = min(self.safety_count + 1, HID_Button.MAX_SAFETY_COUNT)
        else:
            self.safety_count = max(self.safety_count - 1, 0)

        time_since_last_state_change = time.time() - self.time_of_last_state_change

        if time_since_last_state_change < HID_Button.MIN_TIME_BETWEEN_STATE_CHANGE:
            return
        
        safety_check = self.safety_count / HID_Button.MAX_SAFETY_COUNT > HID_Button.SAFETY_FACTOR
        
        if safety_check and not self.button_is_pressed:
            self.button_is_pressed = True
            self.time_of_last_state_change = time.time()
        elif not safety_check and self.button_is_pressed:
            self.button_is_pressed = False
            self.time_of_last_state_change = time.time()

    def is_pressed(self) -> bool:
        return self.button_is_pressed


class HID_Device(ControlDevice):
    """Parent class for HID devices on Raspberry Pi."""

    '''
    name of input i was given to what i think its supposed to be
        "system_key":           SYS_ON
        "e_stop":               ESTOP - NOT USED FOR NOW 
        "sys_select_pos_up":    FILL_SELECTED
        "sys_select_pos_down":  IGNITION_SELECTED
        "fill_switch_pos_up":   N2O_ACTIVE
        "fill_switch_pos_down": PURGE_ACTIVE
        "o2_fill_button":       O2_MOMENT_ACTIVE
        "ignition_button":      IGNITION_MOMENT_ACTIVE
    '''

    HID_VENDOR_ID = 0x0079
    HID_PRODUCT_ID = 0x0006

    # THESE ARE PROB WRONG, wiring has changed since i got these
    # name: (byte, bit)
    BITMAP: Dict[str, Tuple[int, int]] = {
        "SYS_ON":                   (1, 5),
       #"ESTOP":                    (1, 6),
        "FILL_SELECTED":            (0, 2),
        "IGNITION_SELECTED":        (0, 1),
        "N2O_ACTIVE":               (0, 0),
        "PURGE_ACTIVE":             (1, 7),
        "O2_MOMENT_ACTIVE":         (1, 4),
        "IGNITION_MOMENT_ACTIVE":   (1, 3),
    }

    buttons: Dict[str, HID_Button]

    device: hid.Device
    device_is_connected: bool = False

    def _try_connect_device(self):
        try:
            self.device = hid.Device()
            self.device.open(HID_Device.HID_VENDOR_ID, HID_Device.HID_PRODUCT_ID)
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
        slogger.warning("HID_Device is not tested, dont use it untill lab testing has been done")

    def _update_state_table(self):
        """Updates instance attributes"""
        try:
            if not self.device_is_connected: self._try_connect_device()
            if not self.device_is_connected: return None

            bytes = self.device.read(9999)

            for _, btn in self.buttons.items():
                btn.update_state(bytes)

            state_dict: Dict[str: bool] = {btn_name : btn.is_pressed() for btn_name, btn in self.buttons.items()}
            # Temporary fix for neutral state which isn't wired
            state_dict["NEUTRAL_ACTIVE"] = not self.N2O_ACTIVE and not self.PURGE_ACTIVE
            
            self.state_table = StateTable(**state_dict)
                
        except IOError as e:
            self.device_is_connected = False

            self.state_table = StateTable.FALLBACK_DICT

    def cleanup(self):
        self.device.close()


class Pygame_Device(ControlDevice):
    """
        Parent class for Pygame devices on Raspberry Pi.
        Handles all pygame setup and shutdown
    """

    CONTROLLER_MAP = {
        "BTN_A": 0,
        "BTN_B": 1,
        "BTN_X": 2,
        "BTN_Y": 3,
        "BTN_LB": 4,
        "BTN_RB": 5,
        "BTN_BACK": 6,
        "BTN_START": 7,
        "BTN_LOGITECH": 8,
        "BTN_LEFT_JOYSTICK": 9,
        "BTN_RIGHT_JOYSTICK": 10
    }

    KEY_MAP = {
        "SYSTEM_SELECT_TOGGLE_GAS": ("BTN_LEFT_JOYSTICK", False),
        "SYSTEM_SELECT_TOGGLE_IGNITION": ("BTN_RIGHT_JOYSTICK", False),
        "SYSTEM_SELECT_TOGGLE_NEUTRAL": ("BTN_BACK", False),  # NEW
        "GAS_DEADMAN": ("BTN_LB", True),
        "GAS_SELECTION_ROTARY_PURGE": ("BTN_LOGITECH", False),
        "GAS_SELECTION_ROTARY_N2O": ("BTN_X", False),
        "GAS_SELECTION_ROTARY_NEUTRAL": ("BTN_Y", False),  # CHANGED
        "O2_MOMENTARY": ("BTN_B", True),
        "IGNITION_DEADMAN": ("BTN_RB", True),
        "IGNITION_FIRE": ("BTN_A", True),
        "TOGGLE_SYSTEM_ACTIVE": ("BTN_START", False),
    }

    # Used for printing names
    # 'BTN_??': SELECTGION_TOGGLE_GAS???
    KEY_MAP_INVERSE = {v[0]: k for k, v in KEY_MAP.items()}
    # fml again
    BTN_TOGGLE_MAP = {v[0]: v[1] for v in KEY_MAP.values()}

    CONTROLLER_NAME: str = "idk yet"

    joystick: pygame.joystick.JoystickType
    is_connected: bool = False

    def _try_connect_device(self):
        # Attempt controller connection
        if pygame.joystick.get_count() == 0:
            slogger.warning("No Controllers Connected")
            return

        self.is_connected = False

        found_names = ""

        for i in range(pygame.joystick.get_count()):
            temp_joystick = pygame.joystick.Joystick(i)
            temp_joystick.init()
            found_names += temp_joystick.get_name()
            found_names += ", "
            if temp_joystick.get_name() == Pygame_Device.CONTROLLER_NAME:
                self.is_connected = True
                self.joystick = temp_joystick
            
        
        if not self.is_connected:
            slogger.warning("Did not find controller '" + Pygame_Device.CONTROLLER_NAME + "'" + " found controllers '" + found_names + "'")
            return

        slogger.info(f"Controller initialized: {self.joystick.get_name()}")


    def _setup_device(self):
        pygame.init()
        pygame.mixer.quit()  # https: // stackoverflow.com/a/50552161/14141223
        pygame.joystick.init()

        self._try_connect_device()

        
    def __init__(self):
        super().__init__()

    def handle_button_press(button_id, pressed):
        global pressed_states
        button_name = None
        for name, btn_id in Pygame_Device.CONTROLLER_MAP.items():
            if btn_id == button_id:
                button_name = name
                break

        if button_name and button_name in pressed_states:
            action = None
            try:
                toggle_state = Pygame_Device.BTN_TOGGLE_MAP[button_name]
            except KeyError:
                # Pressed an unmpapped button
                return
            if toggle_state == False:
                # This is a toggle switch
                if pressed:
                    # Only operate this on a press, not on a release
                    if Pygame_Device.KEY_MAP_INVERSE[button_name] == "TOGGLE_SYSTEM_ACTIVE":
                        # Repeated press toggle logic for SPST
                        pressed_states[button_name] = not pressed_states[button_name]
                    else:
                        # Set state to true, set others to false logic. for non SPST
                        pressed_states[button_name] = True
                    action = "toggled " + \
                        ("on" if pressed_states[button_name] else "off")
                    # Now if you operated on the SPDT, or rotary, you need to turn off the other options
                    # A SPST switch doesn't need this because it only has one state
                    system_rotary_options = [KEY_MAP["SYSTEM_SELECT_TOGGLE_GAS"][0],
                                            KEY_MAP["SYSTEM_SELECT_TOGGLE_IGNITION"][0],
                                            KEY_MAP["SYSTEM_SELECT_TOGGLE_NEUTRAL"][0]]

                    gas_rotary_options = [KEY_MAP["GAS_SELECTION_ROTARY_PURGE"][0],
                                        KEY_MAP["GAS_SELECTION_ROTARY_N2O"][0],
                                        KEY_MAP["GAS_SELECTION_ROTARY_NEUTRAL"][0]]

                    if button_name in gas_rotary_options:
                        gas_rotary_options.remove(button_name)
                        for reminaing_option in gas_rotary_options:
                            pressed_states[reminaing_option] = False

                    if button_name in system_rotary_options:
                        system_rotary_options.remove(button_name)
                        for reminaing_option in system_rotary_options:
                            pressed_states[reminaing_option] = False
            else:
                # This is a momentary button
                pressed_states[button_name] = pressed
                action = "pressed" if pressed else "released"

            # if action is not None: slogger.debug(f"Controller {button_name} {action}")


    def _update_state_table(self):
        """Updates instance attributes"""

        pygame.event.pump() # seg fault on mac if i dont do this

        events = pygame.event.get()

        for event in events:
            match event.type:
                case pygame.JOYBUTTONDOWN:
                    self.handle_button_press(event.button, True)
                case pygame.JOYBUTTONUP:
                    self.handle_button_press(event.button, False)

        # Temporary fix for neutral state which isn't wired
        self.NEUTRAL_ACTIVE = not self.N2O_ACTIVE and not self.PURGE_ACTIVE
        self.state_table = StateTable(**states)
    
    def cleanup(self):
        """Internal cleaup code"""
        slogger.info("Quitting pygame...")
        pygame.quit()
        slogger.info("Pygame killed. Done...")


def get_control_device(key: str) -> ControlDevice:
    key = key.lower().strip()
    return {
        'rpi_gpio_device': RPI_GPIO_Device,
        'hid_device': HID_Device
    }.get(key, None)


def send_packet():
    context = zmq.Context()
    try:
        push_socket = context.socket(zmq.PUSH)
        CONFIG = config.load_config()
        SOCKET_PATH = os.path.abspath(os.path.join(
            os.path.sep, 'tmp', 'gcs_rocket_pendant_pull.sock')
        )
        CONTROL_TYPE = CONFIG['hardware']['controller']
        controller: ControlDevice = get_control_device(CONTROL_TYPE)()
        # Wait LINGER_TIME_MS before giving up on push request
        LINGER_TIME_MS = 300

        push_socket.setsockopt(zmq.LINGER, LINGER_TIME_MS)
        push_socket.setsockopt(zmq.SNDHWM, 1)  # Limit send buffer to 1 message
        push_socket.connect(f"ipc://{SOCKET_PATH}")

        while not service_helper.time_to_stop():
            # Get values to pass to emulator
            # These states are validated, error checked and include fallback
            states = controller.get_states_dict()
            state_command = device_emulator.GCStoGSEStateCMD(**states)
            try:
                push_socket.send(
                    state_command.get_payload_bytes(EXTERNAL=True), flags=zmq.NOBLOCK)
            except zmq.ZMQError:
                # Queue is likely full
                slogger.warning(
                    "ZMQ Push socket is full. Cannot send data until it is emptied in server. Sleeping")
                time.sleep(1)
            # No need to go full blast.
            time.sleep(0.05)
    finally:
        slogger.debug("Packet sender closing socket")
        push_socket.close()
        slogger.debug("Packet sender closed socket")
        slogger.debug(f"Packet sender closing context (<{LINGER_TIME_MS}ms)")
        context.term()
        slogger.debug("Packet sender thread resources cleaned up")
        slogger.debug("Cleaning up controller")
        controller.cleanup()
        slogger.debug("Cleaned up controller")


def main():
    device_emulator.MockPacket.initialize_settings(
        config.load_config()['emulation'])
    slogger.debug("Starting pendant emulator")

    # global packet_thread
    # packet_thread = threading.Thread(target=send_packet)
    # packet_thread.start()
    send_packet()

if __name__ == "__main__":
    main()
