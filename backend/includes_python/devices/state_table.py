import backend.includes_python.process_logging as slogger
from typing import Self, Dict
from enum import Enum

class PendantInput(Enum):
    """
    Represents an input from the physical pendant device
    """
    # important stuff
    SYSTEM_ACTIVE = "SYSTEM_ACTIVE"
    E_STOP = "E_STOP"

    # first toggle (selector switch)
    FILL_MODE = "FILL_MODE"
    STANDBY = "STANDBY"
    ARMED = "ARMED"

    # second toggle
    N2O = "N2O"
    NEUTRAL = "NEUTRAL"
    PURGE = "PURGE"

    # buttons
    O2 = "O2"
    IGNITION = "IGNITION"

class GSEState(Enum):
    """
    Represents a state to be sent to GSE
    """
    # important stuff
    SYSTEM_ACTIVE = "SYS_ON"

    # first toggle
    FILL_MODE = "FILL_SELECTED"
    ARMED = "IGNITION_SELECTED"

    # second toggle
    N2O = "N2O_ACTIVE"
    NEUTRAL = "NEUTRAL_ACTIVE"
    PURGE = "PURGE_ACTIVE"

    # buttons
    O2 = "O2_MOMENT_ACTIVE"
    IGNITION = "IGNITION_MOMENT_ACTIVE"




class StateTable:
    """
    Stores the states (argument) for the GSE to GCS packet. bonza cunt
    """

    FALLBACK_DICT = {
        "SYS_ON": False,
        "FILL_SELECTED": False,
        "IGNITION_SELECTED": False,
        "N2O_ACTIVE": False,
        "NEUTRAL_ACTIVE": False,
        "PURGE_ACTIVE": False,
        "O2_MOMENT_ACTIVE": False,
        "IGNITION_MOMENT_ACTIVE": False,
    }

    @staticmethod
    def _bool_table_str(printable_dict: dict) -> str:
        MAX_KEY_LEN = max(len(str(k)) for k in printable_dict)
        output = ""
        for k, v in printable_dict.items():
            assert isinstance(v, bool)
            symbol = "[X]" if v else "[ ]"
            output += f"{k:<{MAX_KEY_LEN}} : {symbol}\n"
        return output

    def __str__(self):
        mock_states = self.get_states_dict()
        return StateTable._bool_table_str(mock_states)

    def __repr__(self):
        """Debug print statement"""
        debug_attributes = {
            "SYS_ON": self.SYS_ON,
            "FILL_SELECTED": self.FILL_SELECTED,
            "IGNITION_SELECTED": self.IGNITION_SELECTED,
            "N2O_ACTIVE": self.N2O_ACTIVE,
            "NEUTRAL_ACTIVE": self.NEUTRAL_ACTIVE,
            "PURGE_ACTIVE": self.PURGE_ACTIVE,
            "O2_MOMENT_ACTIVE": self.O2_MOMENT_ACTIVE,
            "IGNITION_MOMENT_ACTIVE": self.IGNITION_MOMENT_ACTIVE,
        }
        # Get string of outputs
        output = StateTable._bool_table_str(debug_attributes)
        # Get string if calculated packet states
        output += "\n"
        output += self.__str__()
        return output

    def __eq__(self, other):
        if not isinstance(other, StateTable):
            return NotImplemented
        return self.get_states_dict() == other.get_states_dict()

    def __ne__(self, other):
        return not self == other

    def __init__(
        self,
        SYS_ON: bool = True,
        FILL_SELECTED: bool = True,
        IGNITION_SELECTED: bool = True,
        N2O_ACTIVE: bool = True,
        NEUTRAL_ACTIVE: bool = True,
        PURGE_ACTIVE: bool = True,
        O2_MOMENT_ACTIVE: bool = True,
        IGNITION_MOMENT_ACTIVE: bool = True,
        ESTOP: bool = False,
    ):
        self.SYS_ON = SYS_ON
        self.FILL_SELECTED = FILL_SELECTED
        self.IGNITION_SELECTED = IGNITION_SELECTED
        self.N2O_ACTIVE = N2O_ACTIVE
        self.NEUTRAL_ACTIVE = NEUTRAL_ACTIVE
        self.PURGE_ACTIVE = PURGE_ACTIVE
        self.O2_MOMENT_ACTIVE = O2_MOMENT_ACTIVE
        self.IGNITION_MOMENT_ACTIVE = IGNITION_MOMENT_ACTIVE
        self.ESTOP = ESTOP

    def get_states_dict(self) -> dict[str, bool]:
        """returns argument dictionary for use in GCS to GSE packet"""
        # You should also check these states electronically where applicable
        # fmt: off
        states = {
            "MANUAL_PURGE": self.SYS_ON and self.FILL_SELECTED and self.PURGE_ACTIVE,
            "O2_FILL_ACTIVATE": self.SYS_ON and self.IGNITION_SELECTED and self.O2_MOMENT_ACTIVE,
            "SELECTOR_SWITCH_NEUTRAL_POSITION": self.SYS_ON and self.FILL_SELECTED and self.NEUTRAL_ACTIVE,
            "N2O_FILL_ACTIVATE": self.SYS_ON and self.FILL_SELECTED and self.N2O_ACTIVE,
            "IGNITION_FIRE": self.SYS_ON and self.IGNITION_SELECTED and self.IGNITION_MOMENT_ACTIVE,
            "IGNITION_SELECTED": self.SYS_ON and self.IGNITION_SELECTED,
            "GAS_FILL_SELECTED": self.SYS_ON and self.FILL_SELECTED,
            "SYSTEM_ACTIVATE": self.SYS_ON,
        }
        # fmt: on

        # Type and range validation
        if (
            any(not isinstance(x, bool) for x in states.values())
            or len(states) != 8
        ):
            slogger.error(f"Missing/invalid states: {states}")
            return StateTable.get_fallback_table()

        # Nonsensical states that should not exist. GSE will complain if any true
        nonsensical_conditions = {
            "purge and fill": states["MANUAL_PURGE"]
            and states["O2_FILL_ACTIVATE"],
            "purge on neutral": states["MANUAL_PURGE"]
            and states["SELECTOR_SWITCH_NEUTRAL_POSITION"],
            # states["MANUAL_PURGE"] and states["SELECTOR_SWITCH_NEUTRAL_POSITION"]
            # add more. please do this automatically
        }

        for k, v in nonsensical_conditions.items():
            if v:
                slogger.warning(f"Impossible condition detected: {k}")
                states = StateTable.FALLBACK_DICT

        return states

    def get_fallback_table() -> Self:
        """Return an instance of StateTable which is safe"""
        return StateTable(**StateTable.FALLBACK_DICT)