"""
This has not been tested or even ran at all
Most likely will have some runtime error if you try it
Test the crap out of it and fix any bugs before using
"""

from backend.includes_python.devices.pendant_state import (
    PendantState,
    PendantInput,
)
from backend.includes_python.devices.control_device import ControlDevice
import backend.includes_python.process_logging as slogger

import time

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
        def Device(self) -> None:
            raise NotImplementedError(error_message)


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

    def __init__(self, byte: int, bit: int):
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

    def update_state(self, hid_bytes: list[int]) -> None:
        if len(hid_bytes) < 7:
            slogger.error(
                f"hid_bytes is too small, expected 7, got {len(hid_bytes)}"
            )
            return

        byte_index = HID_Button.USEFUL_BYTE_OFFSET + self.byte
        hid_byte = hid_bytes[byte_index]

        self._try_update_state(bool(hid_byte & self.bitmask))

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
    BITMAP: Dict[PendantInput, Tuple[int, int]] = {
        PendantInput.SYSTEM_ACTIVE: (1, 5),
        PendantInput.E_STOP: (1, 6),
        PendantInput.FILL_MODE: (0, 2),
        PendantInput.ARMED: (0, 1),
        PendantInput.N2O: (0, 0),
        PendantInput.PURGE: (1, 7),
        PendantInput.O2: (1, 4),
        PendantInput.IGNITION: (1, 3),
    }

    buttons: Dict[PendantInput, HID_Button]

    device: hid.Device
    device_is_connected: bool = False

    def _try_connect_device(self):
        try:
            self.device = hid.Device()
            self.device.open(
                HID_Device.HID_VENDOR_ID, HID_Device.HID_PRODUCT_ID
            )
            self.device_is_connected = True
        except OSError as e:
            # TODO: stop spamming the slogger
            slogger.warning(f"Control Pendant is not connected, error: `{e}`")
            self.device_is_connected = False

    def _setup_device(self):
        self._try_connect_device()

    def __init__(self):
        super().__init__()

        for btn_name in HID_Device.BITMAP:
            self.buttons[btn_name] = HID_Button(*HID_Device.BITMAP[btn_name])

        slogger.critical("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        slogger.critical("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        slogger.critical(
            "HID_Device is not tested, dont use it until lab testing has been done"
        )
        slogger.critical("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        slogger.critical("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    def _update_state_table(self):
        """Updates instance attributes"""
        try:
            if not self.device_is_connected:
                self._try_connect_device()
            if not self.device_is_connected:
                return

            bytes = self.device.read(9999)

            for _, btn in self.buttons.items():
                btn.update_state(bytes)

            states: Dict[PendantInput, bool] = {
                btn_name: btn.is_pressed()
                for btn_name, btn in self.buttons.items()
            }

            self.state_table = PendantState(states)

        except OSError:
            self.device_is_connected = False
            self.state_table = PendantState.get_fallback_table()

    def cleanup(self):
        self.device.close()
