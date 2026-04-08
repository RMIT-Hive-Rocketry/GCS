from backend.includes_python.devices.pendant_state import (
    PendantState,
    PendantInput,
)
from backend.includes_python.devices.control_device import ControlDevice
import backend.includes_python.process_logging as slogger

import pygame

import time
from abc import abstractmethod
from functools import cached_property
from backend.includes_python.timers import RepeatingTimer


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


class Pygame_Device(ControlDevice):
    """
    ABC for devices that use pygame
    If your extending it, you must define BUTTON_NAME_ID_MAP in the child
    """

    # https://stackoverflow.com/questions/5960337/how-to-create-abstract-properties-in-python-abstract-classes
    @property
    @abstractmethod
    def BUTTON_NAME_ID_MAP(self) -> Dict[PendantInput, int]:
        pass

    @property
    @abstractmethod
    def CONTROLLER_NAME(self) -> str:
        pass

    # dont recompute every time
    @cached_property
    def BUTTON_ID_NAME_MAP(self) -> Dict[int, PendantInput]:
        return {v: k for k, v in self.BUTTON_NAME_ID_MAP.items()}

    buttons: Dict[PendantInput, Pygame_Button]

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
        for but_name, _ in self.BUTTON_NAME_ID_MAP.items():
            self.buttons[but_name] = Pygame_Button()

    def _try_connect_device(self):
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

    def _setup_device(self):
        # https://stackoverflow.com/questions/32900155/pygame-headless-setup
        pygame.display.init()
        pygame.joystick.init()
        self._try_connect_device()

    def _update_state_table(self):
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
            # polling events on mac gave me segfaults
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
