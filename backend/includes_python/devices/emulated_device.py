from backend.includes_python.devices.state_table import StateTable
from backend.includes_python.devices.pygame_device import Pygame_Device
import backend.includes_python.process_logging as slogger
from typing import Dict
import pygame
import time


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
