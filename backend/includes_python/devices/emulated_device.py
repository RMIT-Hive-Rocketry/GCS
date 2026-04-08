from backend.includes_python.devices.pendant_state import PendantState, PendantInput
from backend.includes_python.devices.pygame_device import Pygame_Device
import backend.includes_python.process_logging as slogger
import pygame
import time


class Emulated_Device(Pygame_Device):
    """
    Emulated device class, FOR TESTING ONLY
    Based on the Pygame_Device class, even though it doesn't actually use Pygame
    """

    BUTTON_INPUT_MAP: Dict[PendantInput, int] = {
        PendantInput.SYSTEM_ACTIVE: 0,
        PendantInput.E_STOP: 5,
        PendantInput.FILL_MODE: 6,
        PendantInput.ARMED: 4,
        PendantInput.N2O: 8,
        PendantInput.PURGE: 3,
        PendantInput.O2: 1,
        PendantInput.IGNITION: 2,
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
            states[PendantInput.SYSTEM_ACTIVE] = not states[PendantInput.E_STOP]
            self.state_table = PendantState(states)
        else:
            self.state_table = PendantState.get_fallback_table()

    def cleanup(self):
        """Internal cleanup code"""
        slogger.info("Quitting pygame...")
        pygame.quit()
        slogger.info("Pygame killed. Done...")
