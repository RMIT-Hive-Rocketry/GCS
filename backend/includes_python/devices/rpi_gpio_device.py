from backend.includes_python.devices.control_device import ControlDevice
from backend.includes_python.devices.state_table import StateTable
import backend.includes_python.process_logging as slogger

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
