from backend.includes_python.devices.pygame_device import Pygame_Device

class HybridPygamePendant(Pygame_Device):
    BUTTON_NAME_ID_MAP = {
        "SYS_ON": 0,
        "ESTOP": 5,
        "FILL_SELECTED": 6,
        "IGNITION_SELECTED": 4,
        "N2O_ACTIVE": 8,
        "PURGE_ACTIVE": 3,
        "O2_MOMENT_ACTIVE": 1,
        "IGNITION_MOMENT_ACTIVE": 2,
    }

    CONTROLLER_NAME = "DragonRise Inc. Generic USB Joystick"

class ThrustmasterAirbusFlightStick(Pygame_Device):
    BUTTON_NAME_ID_MAP = {
        "SYS_ON": 16,  # thrust
        "ESTOP": 3,
        "FILL_SELECTED": 1,  # top trigger
        "IGNITION_SELECTED": 0,  # bottom trigger
        "N2O_ACTIVE": 7,  # bottom left button on right side
        "PURGE_ACTIVE": 2,  # spherical button
        "O2_MOMENT_ACTIVE": 6,  # top left button on right side
        "IGNITION_MOMENT_ACTIVE": 8,  # something idk
    }

    CONTROLLER_NAME = "Thrustmaster T.A320 Pilot"

# this ones for Freddy
# sorry it doesnt have all the cool toggle logic :/
# I tried to match the buttons best I could
class LogitechGamepadF710(Pygame_Device):
    BUTTON_NAME_ID_MAP = {
        "SYS_ON": 7,
        "ESTOP": 3,
        "FILL_SELECTED": 2,
        "IGNITION_SELECTED": 10, 
        "N2O_ACTIVE": 9,
        "PURGE_ACTIVE": 4,  # spherical button
        "O2_MOMENT_ACTIVE": 1,  # top left button on right side
        "IGNITION_MOMENT_ACTIVE": 0,  # something idk
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