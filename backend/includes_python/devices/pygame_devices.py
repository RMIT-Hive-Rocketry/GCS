from backend.includes_python.devices.pygame_device import Pygame_Device
from backend.includes_python.devices.pendant_state import PendantInput


class HybridPygamePendant(Pygame_Device):
    BUTTON_NAME_ID_MAP = {
        PendantInput.SYSTEM_ACTIVE: 2,
        PendantInput.E_STOP: 5,
        PendantInput.FILL_MODE: 6,
        PendantInput.ARMED: 4,
        PendantInput.N2O: 8,
        PendantInput.PURGE: 3,
        PendantInput.O2: 1,
        PendantInput.IGNITION: 0,
    }

    CONTROLLER_NAME = "DragonRise Inc. Generic USB Joystick"


class ThrustmasterAirbusFlightStick(Pygame_Device):
    BUTTON_NAME_ID_MAP = {
        PendantInput.SYSTEM_ACTIVE: 16,  # thrust
        PendantInput.E_STOP: 3,
        PendantInput.FILL_MODE: 1,  # top trigger
        PendantInput.ARMED: 0,  # bottom trigger
        PendantInput.N2O: 7,  # bottom left button on right side
        PendantInput.PURGE: 2,  # spherical button
        PendantInput.O2: 6,  # top left button on right side
        PendantInput.IGNITION: 8,  # something idk
    }

    CONTROLLER_NAME = "Thrustmaster T.A320 Pilot"


# this ones for Freddy
# sorry it doesnt have all the cool toggle logic :/
# I tried to match the buttons best I could
class LogitechGamepadF710(Pygame_Device):
    BUTTON_NAME_ID_MAP = {
        PendantInput.SYSTEM_ACTIVE: 7,
        PendantInput.E_STOP: 3,
        PendantInput.FILL_MODE: 2,
        PendantInput.IGNITION: 10,
        PendantInput.N2O: 9,
        PendantInput.PURGE: 4,  # spherical button
        PendantInput.O2: 1,  # top left button on right side
        PendantInput.IGNITION: 0,  # something idk
    }

    CONTROLLER_NAME = "Logitech Gamepad F710"


# controler map for F710 if needed later
# CONTROLLER_MAP = {
#     "BTN_A": 0,
#     "BTN_B": 1,
#     "BTN_X": 2,
#     "BTN_Y": 3,
#     "BTN_LB": 4,
#     "BTN_RB": 5,
#     "BTN_BACK": 6,
#     "BTN_START": 7,
#     "BTN_LOGITECH": 8,
#     "BTN_LEFT_JOYSTICK": 9,
#     "BTN_RIGHT_JOYSTICK": 10,
# }
