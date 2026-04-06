import backend.includes_python.process_logging as slogger
from typing import Self, Dict, Tuple
from enum import Enum

class PendantInput(Enum):
    """
    Represents an input from the physical pendant device
    """
    # important stuff
    SYSTEM_ACTIVE = "SYSTEM_ACTIVE"
    E_STOP = "E_STOP"

    # first toggle
    FILL_MODE = "FILL_MODE"
    ARMED = "ARMED"

    # second toggle
    N2O = "N2O"
    PURGE = "PURGE"

    # buttons
    O2 = "O2"
    IGNITION = "IGNITION"

class GSEState(Enum):
    """
    Represents a state to be sent to GSE
    Enum values correspond to legacy names used for device_emulator
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


class StateTable2:
    """
    Stores state of the pendant
    Has methods which return a Dict suitable for conversion to a GSE packet
    Also has two fallback dicts for the GSE and Pendant
    """
    
    FALLBACK_PENDANT_STATES_DICT: Dict[PendantInput, bool] = {
        pi : False for pi in PendantInput
    }

    FALLBACK_GSE_STATES_DICT: Dict[GSEState, bool] = {
        gs : False for gs in GSEState
    }

    states: Dict[PendantInput, bool]

    def __init__(self, states: Dict[PendantInput, bool]):
        # states can be a subset, and all other inputs will be assumed false

        # make sure all the keys are valid
        for key in states:
            if key not in PendantInput:
                slogger.critical(f"key: {key} is not a PendantInput")
                raise TypeError(f"key: {key} is not a PendantInput")
        
        self.states = {}

        # build states, assuming any missing input is false
        for key, fallback_value in self.FALLBACK_PENDANT_STATES_DICT.items():
            if key in states:
                self.states[key] = states[key]
            else:
                self.states[key] = fallback_value

    def get_gse_states(self) -> Dict[GSEState, bool]:
        REQUIRED_TRUE = "required true"
        REQUIRED_FALSE = "required false"
        NONSENSE_TO_BE_TRUE = "nonsense true"

        # REQUIRED_TRUE are all pendant that must be true for the gse state to be true
        # REQUIRED_FALSE are all the pendant states that are required to be off, but is okay if it is on
        # NONSENSE_TO_BE_TRUE are all the pendant states that do not make logical sense to be on, given the GSEState evaluates to true

        # fmt: off    
        conditions: Dict[GSEState, Dict[str, Tuple[PendantInput]]] = {
            GSEState.SYSTEM_ACTIVE: {
                REQUIRED_TRUE: (PendantInput.SYSTEM_ACTIVE,),
                REQUIRED_FALSE: (PendantInput.E_STOP,),
                NONSENSE_TO_BE_TRUE: ()
            },

            GSEState.FILL_MODE: {
                REQUIRED_TRUE: (PendantInput.SYSTEM_ACTIVE, PendantInput.FILL_MODE),
                REQUIRED_FALSE: (PendantInput.E_STOP,),
                NONSENSE_TO_BE_TRUE: (PendantInput.ARMED, PendantInput.O2, PendantInput.IGNITION)
            },

            GSEState.ARMED: {
                REQUIRED_TRUE: (PendantInput.SYSTEM_ACTIVE, PendantInput.ARMED),
                REQUIRED_FALSE: (PendantInput.E_STOP,),
                NONSENSE_TO_BE_TRUE: (PendantInput.FILL_MODE, PendantInput.N2O, PendantInput.PURGE)
            },

            GSEState.N2O: {
                REQUIRED_TRUE: (PendantInput.SYSTEM_ACTIVE, PendantInput.FILL_MODE, PendantInput.N2O),
                REQUIRED_FALSE: (PendantInput.E_STOP,),
                NONSENSE_TO_BE_TRUE: (PendantInput.PURGE, PendantInput.ARMED, PendantInput.O2, PendantInput.IGNITION)
            },

            GSEState.NEUTRAL: {
                REQUIRED_TRUE: (PendantInput.SYSTEM_ACTIVE, PendantInput.FILL_MODE),
                REQUIRED_FALSE: (PendantInput.E_STOP, PendantInput.N2O, PendantInput.PURGE),
                NONSENSE_TO_BE_TRUE: (PendantInput.ARMED, PendantInput.O2, PendantInput.IGNITION)
            },

            GSEState.PURGE: {
                REQUIRED_TRUE: (PendantInput.SYSTEM_ACTIVE, PendantInput.FILL_MODE, PendantInput.PURGE),
                REQUIRED_FALSE: (PendantInput.E_STOP,),
                NONSENSE_TO_BE_TRUE: (PendantInput.N2O, PendantInput.ARMED, PendantInput.O2, PendantInput.IGNITION)
            },

            GSEState.O2: {
                REQUIRED_TRUE: (PendantInput.SYSTEM_ACTIVE, PendantInput.ARMED, PendantInput.O2),
                REQUIRED_FALSE: (PendantInput.E_STOP,),
                NONSENSE_TO_BE_TRUE: (PendantInput.FILL_MODE, PendantInput.N2O, PendantInput.PURGE)
            },

            GSEState.IGNITION: {
                REQUIRED_TRUE: (PendantInput.SYSTEM_ACTIVE, PendantInput.ARMED, PendantInput.IGNITION),
                REQUIRED_FALSE: (PendantInput.E_STOP,),
                NONSENSE_TO_BE_TRUE: (PendantInput.FILL_MODE, PendantInput.N2O, PendantInput.PURGE)
            }
        }
        # fmt: on

        gse_state_dict = {}

        # check conditions 
        for state in conditions:
            required_true_conditions = conditions[state][REQUIRED_TRUE]
            required_false_conditions = conditions[state][REQUIRED_FALSE]
            nonsense_conditions = conditions[state][NONSENSE_TO_BE_TRUE]

            state_is_true = True
            
            for required in required_true_conditions:
                if not self.states[required]:
                    state_is_true = False
                    break
            
            for required in required_false_conditions:
                if self.states[required]:
                    state_is_true = False
                    break
            
            if state_is_true:
                for nonsense in nonsense_conditions:
                    if self.states[nonsense]:
                        slogger.warning(f"Impossible Condition detected for {state}: {nonsense}")
                        return StateTable2.FALLBACK_GSE_STATES_DICT
            
            gse_state_dict[state] = state_is_true
        
        return gse_state_dict

    @staticmethod
    def get_fallback_table():
        return StateTable2(StateTable2.FALLBACK_PENDANT_STATES_DICT)
    
    def __str__(self):
        # constant value so the states line up
        KEY_COL_WIDTH = 30
        gse_states = self.get_gse_states()

        # not readable at all but it looks cool :)
        output = "Pendant States:\n"
        output += "".join([f"{key: <{KEY_COL_WIDTH}}: {'[X]' if value else '[ ]'}\n" for key, value in self.states.items()])
        output += "\nGSE States"
        output += "".join([f"{key: <{KEY_COL_WIDTH}}: {'[X]' if value else '[ ]'}\n" for key, value in gse_states.items()])
        return output

    def __repr__(self):
        output = "StateTable2({"
        output += "".join([f"{key}: {'True' if value else 'False'},\n" for key, value in self.states.items()])
        output += "})"
        return output

    def __eq__(self, other: Self):
        print(self.states)
        print(other.states)
        return self.states == other.states

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