from typing_extensions import override
from backend.includes_python.devices.pendant_state import (
    PendantState,
    PendantInput,
)
from backend.includes_python.devices.control_device import ControlDevice
import backend.includes_python.process_logging as slogger
from typing import List, Dict, ClassVar

import pygame

import time
from functools import cached_property
from backend.includes_python.timers import RepeatingTimer


class PygameButton:
    MIN_TIME_BETWEEN_STATE_CHANGE: float = 0.05

    time_of_last_state_change: float
    button_is_pressed: bool = False

    def __init__(self):
        self.time_of_last_state_change = time.time()

    def _try_update_state(self, new_state: bool) -> None:
        time_since_last_state_change = (
            time.time() - self.time_of_last_state_change
        )

        if (
            time_since_last_state_change
            < PygameButton.MIN_TIME_BETWEEN_STATE_CHANGE
        ):
            return

        if new_state and not self.button_is_pressed:
            self.button_is_pressed = True
            self.time_of_last_state_change = time.time()
        elif not new_state and self.button_is_pressed:
            self.button_is_pressed = False
            self.time_of_last_state_change = time.time()

    # will update state if safe to do so
    def update_state(self, new_state: bool) -> None:
        self._try_update_state(new_state)

    def is_pressed(self) -> bool:
        return self.button_is_pressed


class PygameDevice(ControlDevice):
    """
    ABC for devices that use pygame
    If your extending it, you must define BUTTON_NAME_ID_MAP and CONTROLLER_NAME in the child
    """

    BUTTON_NAME_ID_MAP: ClassVar[Dict[PendantInput, int]]
    CONTROLLER_NAME: ClassVar[str]

    # dont recompute every time
    @cached_property
    def button_id_name_map(self) -> dict[int, PendantInput]:
        return {v: k for k, v in self.BUTTON_NAME_ID_MAP.items()}

    buttons: dict[PendantInput, PygameButton]

    joystick: pygame.joystick.JoystickType | None
    joystick_id: int | None
    is_connected: bool

    complain_timer: RepeatingTimer

    def __init__(self):
        self.joystick = None
        self.joystick_id = None
        self.is_connected = False

        self.complain_timer = RepeatingTimer(10)

        super().__init__()
        self.buttons = {}
        for but_name in self.BUTTON_NAME_ID_MAP:
            self.buttons[but_name] = PygameButton()

    def _try_connect_device(self) -> None:
        should_complain = self.complain_timer.time_has_passed()

        # Attempt controller connection
        if pygame.joystick.get_count() == 0:
            if should_complain:
                slogger.warning("No Controllers Connected")
            return

        # Don't re-attempt connection if device is already connected
        if self.is_connected:
            return

        # this should only be called when these are junk (controller disconnected, startup etc)
        # self.is_connected = False
        # self.joystick = None
        found_names = ""

        for i in range(pygame.joystick.get_count()):
            jstk = pygame.joystick.Joystick(i)
            jstk.init()
            found_names += jstk.get_name()
            found_names += ", "
            if jstk.get_name() == self.CONTROLLER_NAME:
                self.is_connected = True
                self.joystick = jstk
                self.joystick_id = jstk.get_instance_id()

                slogger.info(
                    f"Controller initialized: {self.joystick.get_name()}"
                )
                break

        if not self.is_connected:
            if should_complain:
                slogger.warning(
                    "Did not find controller '"
                    + self.CONTROLLER_NAME
                    + "'"
                    + " found controllers '"
                    + found_names
                    + "'"
                )
            return

    @override
    def _setup_device(self) -> None:
        # https://stackoverflow.com/questions/32900155/pygame-headless-setup
        pygame.display.init()
        pygame.joystick.init()
        self._try_connect_device()

    @override
    def _update_state_table(self) -> None:
        """Updates instance attributes"""
        if not self.is_connected:
            self._try_connect_device()

        # check for disconnection
        events: list[pygame.event.Event] = pygame.event.get()
        for event in events:
            if (
                event.type == pygame.JOYDEVICEREMOVED
                and event.instance_id == self.joystick_id
            ):
                self.joystick = None
                self.is_connected = False
                self.joystick_id = 0
                slogger.error("Pendnat Disconnected")

        if self.is_connected and self.joystick is not None:
            for btn_name, btn_id in self.BUTTON_NAME_ID_MAP.items():
                try:
                    pressed = bool(self.joystick.get_button(btn_id))
                except Exception:
                    # Don't automatically disconnect device when an unexpected button is pressed
                    # Since the joystick sends noisy/useless data, it causes it to reconnect endlessly
                    pressed = False
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
