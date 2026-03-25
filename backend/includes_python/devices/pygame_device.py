from backend.includes_python.devices.state_table import StateTable
from backend.includes_python.devices.control_device import ControlDevice
import backend.includes_python.process_logging as slogger

from typing import List, Dict
import pygame
import time

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

    def cleanup(self):
        """Internal cleaup code"""
        slogger.info("Quitting pygame...")
        pygame.quit()
        slogger.info("Pygame killed. Done...")
