from backend.includes_python.devices.pendant_state import (
    PendantState,
    PendantInput,
)
from backend.includes_python.devices.pygame_device import Pygame_Device
import backend.includes_python.process_logging as slogger
import pygame
import time


class Emulated_Device(Pygame_Device):
    """
    Emulated device class, FOR TESTING ONLY
    Based on the Pygame_Device class, even though it doesn't actually use Pygame
    """

    BUTTON_NAME_ID_MAP: dict[PendantInput, int] = {
        PendantInput.SYSTEM_ACTIVE: 0,
        PendantInput.E_STOP: 5,
        PendantInput.FILL_MODE: 6,
        PendantInput.ARMED: 4,
        PendantInput.N2O: 8,
        PendantInput.PURGE: 3,
        PendantInput.O2: 1,
        PendantInput.IGNITION: 2,
    }

    CONTROLLER_NAME = "EMULATED USB CONTROLLER - FOR TESTING ONLY"

    BUTTON_SEQUENCE: list[list[PendantInput]] = [
        [],
        [PendantInput.SYSTEM_ACTIVE],
        [PendantInput.SYSTEM_ACTIVE, PendantInput.FILL_MODE],
        [PendantInput.SYSTEM_ACTIVE, PendantInput.FILL_MODE, PendantInput.N2O],
        [PendantInput.SYSTEM_ACTIVE, PendantInput.FILL_MODE],
        [
            PendantInput.SYSTEM_ACTIVE,
            PendantInput.FILL_MODE,
            PendantInput.PURGE,
        ],
        [PendantInput.SYSTEM_ACTIVE, PendantInput.FILL_MODE],
        [PendantInput.SYSTEM_ACTIVE],
        [],
        [PendantInput.SYSTEM_ACTIVE],
        [PendantInput.SYSTEM_ACTIVE, PendantInput.ARMED],
        [PendantInput.SYSTEM_ACTIVE, PendantInput.ARMED, PendantInput.O2],
        [PendantInput.SYSTEM_ACTIVE, PendantInput.ARMED],
        [PendantInput.SYSTEM_ACTIVE, PendantInput.ARMED, PendantInput.IGNITION],
        [PendantInput.SYSTEM_ACTIVE, PendantInput.ARMED],
        [
            PendantInput.SYSTEM_ACTIVE,
            PendantInput.ARMED,
            PendantInput.O2,
            PendantInput.IGNITION,
        ],
        [PendantInput.SYSTEM_ACTIVE, PendantInput.ARMED],
        [PendantInput.SYSTEM_ACTIVE],
        [],
    ]

    is_connected: bool = False

    def __init__(self):
        super().__init__()

    def _try_connect_device(self) -> None:
        # This device never has connection issues
        Emulated_Device.is_connected = True
        slogger.info(
            f"Controller initialized: {Emulated_Device.CONTROLLER_NAME}"
        )

    def _setup_device(self) -> None:
        pygame.init()
        self._try_connect_device()

    def _update_state_table(self) -> None:
        """Updates instance attributes"""
        pygame.event.pump()

        if Emulated_Device.is_connected:

            # Loop through states and update them
            seconds = int(time.time())
            current_buttons = Emulated_Device.BUTTON_SEQUENCE[
                seconds % len(Emulated_Device.BUTTON_SEQUENCE)
            ]

            for btn_name in Emulated_Device.BUTTON_NAME_ID_MAP:
                pressed = btn_name in current_buttons
                self.buttons[btn_name].update_state(pressed)

            states = {
                btn_name: btn.is_pressed()
                for btn_name, btn in self.buttons.items()
            }

            self.state_table = PendantState(states)

        else:
            self.state_table = PendantState.get_fallback_table()

    def cleanup(self) -> None:
        """Internal cleanup code"""
        slogger.info("Quitting pygame...")
        pygame.quit()
        slogger.info("Pygame killed. Done...")
