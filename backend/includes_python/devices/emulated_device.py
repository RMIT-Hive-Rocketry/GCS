from typing_extensions import override
from backend.includes_python.devices.pendant_state import (
    PendantState,
    PendantInput,
)
from backend.includes_python.devices.pygame_device import PygameDevice
import backend.includes_python.process_logging as slogger
import pygame
import time


class EmulatedDevice(PygameDevice):
    """
    Emulated device class, FOR TESTING ONLY
    Based on the PygameDevice class, even though it doesn't actually use Pygame
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
        [PendantInput.E_STOP],
        [],
    ]

    is_connected: bool = False

    def __init__(self):
        super().__init__()

    @override
    def _try_connect_device(self) -> None:
        # This device never has connection issues
        EmulatedDevice.is_connected = True
        slogger.info(
            f"Controller initialized: {EmulatedDevice.CONTROLLER_NAME}"
        )

    @override
    def _setup_device(self) -> None:
        _ = pygame.init()
        self._try_connect_device()

    @override
    def _update_state_table(self) -> None:
        """Updates instance attributes"""
        pygame.event.pump()

        if EmulatedDevice.is_connected:

            # Loop through states and update them
            seconds = int(time.time())
            current_buttons = EmulatedDevice.BUTTON_SEQUENCE[
                seconds % len(EmulatedDevice.BUTTON_SEQUENCE)
            ]

            for btn_name in EmulatedDevice.BUTTON_NAME_ID_MAP:
                pressed = btn_name in current_buttons
                self.buttons[btn_name].update_state(pressed)

            states = {
                btn_name: btn.is_pressed()
                for btn_name, btn in self.buttons.items()
            }

            self.state_table: PendantState = PendantState(states)

        else:
            self.state_table = PendantState.get_fallback_table()

    @override
    def cleanup(self) -> None:
        """Internal cleanup code"""
        slogger.info("Quitting pygame...")
        pygame.quit()
        slogger.info("Pygame killed. Done...")
