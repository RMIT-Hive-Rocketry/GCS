import backend.includes_python.process_logging as slogger
from typing import Dict, Tuple
from enum import StrEnum


class PendantInput(StrEnum):
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


class GSEState(StrEnum):
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


class PendantState:
    """
    Stores state of the pendant
    Has methods which return a Dict suitable for conversion to a GSE packet
    Also has two fallback dicts for the GSE and Pendant
    """

    FALLBACK_PENDANT_STATES_DICT: Dict[PendantInput, bool] = {
        # important stuff
        PendantInput.SYSTEM_ACTIVE: True,
        PendantInput.E_STOP: False,
        # first toggle
        PendantInput.FILL_MODE: False,
        PendantInput.ARMED: False,
        # second toggle
        PendantInput.N2O: False,
        PendantInput.PURGE: False,
        # buttons
        PendantInput.O2: False,
        PendantInput.IGNITION: False,
    }

    FALLBACK_GSE_STATES_DICT: Dict[GSEState, bool] = {
        GSEState.SYSTEM_ACTIVE: True,
        # first toggle
        GSEState.FILL_MODE: False,
        GSEState.ARMED: False,
        # second toggle
        GSEState.N2O: False,
        GSEState.NEUTRAL: False,
        GSEState.PURGE: False,
        # buttons
        GSEState.O2: False,
        GSEState.IGNITION: False,
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
        for key, _ in self.FALLBACK_PENDANT_STATES_DICT.items():
            if key in states:
                self.states[key] = states[key]
            else:
                self.states[key] = False

    def get_gse_states(self) -> Dict[GSEState, bool]:
        REQUIRED_TRUE = "required true"
        REQUIRED_FALSE = "required false"
        NONSENSE_TO_BE_TRUE = "nonsense true"

        # REQUIRED_TRUE are all pendant that must be true for the gse state to be true
        # REQUIRED_FALSE are all the pendant states that are required to be off, but is okay if it is on
        # NONSENSE_TO_BE_TRUE are all the pendant states that do not make logical sense to be on, given the GSEState evaluates to true

        # fmt: off
        conditions: Dict[GSEState, Dict[str, Tuple[PendantInput, ...]]] = {
            GSEState.SYSTEM_ACTIVE: {
                REQUIRED_TRUE: (PendantInput.SYSTEM_ACTIVE,),
                REQUIRED_FALSE: (PendantInput.E_STOP,),
                NONSENSE_TO_BE_TRUE: tuple()
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

        gse_state_dict: Dict[GSEState, bool] = {}

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
                        slogger.warning(
                            f"Impossible Condition detected for {state}: {nonsense}"
                        )
                        return PendantState.FALLBACK_GSE_STATES_DICT

            gse_state_dict[state] = state_is_true

        return gse_state_dict

    @staticmethod
    def get_fallback_table():
        return PendantState(PendantState.FALLBACK_PENDANT_STATES_DICT)

    def __str__(self):        
        gse_states = self.get_gse_states()
        KEY_COL_WIDTH = max([len(key) for key, _ in gse_states.items()])
        print(KEY_COL_WIDTH)
        
        output = "\033[1mPendant States: \033[0m\n"
        output += "".join(
            [
                f"{key: <{KEY_COL_WIDTH}}: {'[X]' if value else '[ ]'}\n"
                for key, value in self.states.items()
            ]
        )
        output += "\n\033[1mGSE States: \033[0m\n"
        output += "".join(
            [
                f"{key: <{KEY_COL_WIDTH}}: {'[X]' if value else '[ ]'}\n"
                for key, value in gse_states.items()
            ]
        )
        return output

    def __repr__(self):
        output = "PendantState({"
        output += "".join(
            [
                f"PendantInput.{key}: {'True' if value else 'False'},"
                for key, value in self.states.items()
            ]
        )
        output += "})"
        return output

    def __eq__(self, other: object):
        if not isinstance(other, PendantState):
            return NotImplemented
        return self.states == other.states
