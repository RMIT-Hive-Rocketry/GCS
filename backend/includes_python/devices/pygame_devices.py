from backend.includes_python.devices.pygame_device import PygameDevice
from backend.includes_python.devices.pendant_state import PendantInput


# This is the mapping of the orange controller
# We need to formalise this into a wiring diagram
# so that future hybrid pendants will match it
class HybridPygamePendant(PygameDevice):
    BUTTON_NAME_ID_MAP = {
        PendantInput.IGNITION: 0,
        PendantInput.O2: 1,
        PendantInput.SYSTEM_ACTIVE: 2,
        PendantInput.PURGE: 3,
        PendantInput.ARMED: 4,
        PendantInput.E_STOP: 5,
        PendantInput.FILL_MODE: 6,
        PendantInput.F9: 7,
        PendantInput.N2O: 8,
        PendantInput.F10: 9,
        PendantInput.F11: 10,
        PendantInput.F12: 11,
    }

    CONTROLLER_NAME = "DragonRise Inc. Generic USB Joystick"


class ThrustmasterAirbusFlightStick(PygameDevice):
    BUTTON_NAME_ID_MAP = {
        PendantInput.FILL_MODE: 0,  # bottom back trigger
        PendantInput.ARMED: 1,  # top back trigger
        PendantInput.O2: 2,  # spherical button
        PendantInput.IGNITION: 3,  # red button
        # 4
        PendantInput.PURGE: 5,  # top middle button on the right
        PendantInput.N2O: 6,  # top left button on the right
        # 7
        PendantInput.F9: 8,
        PendantInput.F10: 9,
        PendantInput.F11: 10,
        PendantInput.F12: 11,
        # 12
        PendantInput.E_STOP: 13,  # bottom right button on the left
        # 14
        # 15
        PendantInput.SYSTEM_ACTIVE: 16,  # thrust lever
    }

    CONTROLLER_NAME = "Thrustmaster T.A320 Pilot"


# this ones for Freddy
# sorry it doesn't have all the cool toggle logic :/
# I tried to match the buttons best I could
class LogitechGamepadF710(PygameDevice):
    BUTTON_NAME_ID_MAP = {
        PendantInput.IGNITION: 0,  # something idk
        PendantInput.O2: 1,  # top left button on right side
        PendantInput.FILL_MODE: 2,
        PendantInput.E_STOP: 3,
        PendantInput.PURGE: 4,  # spherical button
        # 5
        # 6
        PendantInput.SYSTEM_ACTIVE: 7,
        # 8
        PendantInput.N2O: 9,
        PendantInput.IGNITION: 10,
    }

    CONTROLLER_NAME = "Logitech Gamepad F710"


# controller map for F710 if needed later
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
