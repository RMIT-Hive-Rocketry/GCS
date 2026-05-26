from typing_extensions import override
import backend.includes_python.process_logging as slogger
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

    # spare/function buttons, for rebindable inputs
    # currently not used
    F9 = "F9"
    F10 = "F10"
    F11 = "F11"
    F12 = "F12"


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

    # spare/function buttons
    F9 = "F9"
    F10 = "F10"
    F11 = "F11"
    F12 = "F12"


class PendantState:  # noqa: PLW1641
    """
    Stores state of the pendant
    Has methods which return a Dict suitable for conversion to a GSE packet
    Also has three fallback dicts for the GSE and Pendant
    """

    FALLBACK_PENDANT_STATES_DICT: dict[PendantInput, bool] = dict.fromkeys(
        PendantInput, False
    )
    FALLBACK_GSE_STATES_DICT: dict[GSEState, bool] = dict.fromkeys(
        GSEState, False
    )
    FALLBACK_GSE_STATES_DICT_SYS_ON: dict[GSEState, bool] = dict.fromkeys(
        GSEState, False
    )
    FALLBACK_GSE_STATES_DICT_SYS_ON[GSEState.SYSTEM_ACTIVE] = True

    states: dict[PendantInput, bool]

    def __init__(self, states: dict[PendantInput, bool]):
        # states can be a subset, and all other inputs will be assumed false

        # make sure all the keys are valid
        for key in states:
            if not isinstance(key, PendantInput):
                slogger.critical(f"key: {key} is not a PendantInput")
                raise TypeError(f"key: {key} is not a PendantInput")

        self.states = {}

        # build states, assuming any missing input is false
        for key in self.FALLBACK_PENDANT_STATES_DICT:
            self.states[key] = states.get(key, False)

    def get_pendant_states(self) -> dict[PendantInput, bool]:
        return self.states

    def get_gse_states(self) -> dict[GSEState, bool]:
        required_true = "required true"
        required_false = "required false"
        nonsense_to_be_true = "nonsense true"

        # required_true are all pendant that must be true for the gse state to be true
        # required_false are all the pendant states that are required to be off, but is okay if it is on
        # nonsense_to_be_true are all the pendant states that do not make logical sense to be on, given the GSEState evaluates to true

        # fmt: off
        conditions: dict[GSEState, dict[str, tuple[PendantInput, ...]]] = {
            GSEState.SYSTEM_ACTIVE: {
                required_true: (PendantInput.SYSTEM_ACTIVE,),
                required_false: (PendantInput.E_STOP,),
                nonsense_to_be_true: ()
            },

            GSEState.FILL_MODE: {
                required_true: (PendantInput.SYSTEM_ACTIVE, PendantInput.FILL_MODE),
                required_false: (PendantInput.E_STOP,),
                nonsense_to_be_true: (PendantInput.ARMED, PendantInput.O2, PendantInput.IGNITION)
            },

            GSEState.ARMED: {
                required_true: (PendantInput.SYSTEM_ACTIVE, PendantInput.ARMED),
                required_false: (PendantInput.E_STOP,),
                nonsense_to_be_true: (PendantInput.FILL_MODE, PendantInput.N2O, PendantInput.PURGE)
            },

            GSEState.N2O: {
                required_true: (PendantInput.SYSTEM_ACTIVE, PendantInput.FILL_MODE, PendantInput.N2O),
                required_false: (PendantInput.E_STOP,),
                nonsense_to_be_true: (PendantInput.PURGE, PendantInput.ARMED, PendantInput.O2, PendantInput.IGNITION)
            },

            GSEState.NEUTRAL: {
                required_true: (PendantInput.SYSTEM_ACTIVE, PendantInput.FILL_MODE),
                required_false: (PendantInput.E_STOP, PendantInput.N2O, PendantInput.PURGE),
                nonsense_to_be_true: (PendantInput.ARMED, PendantInput.O2, PendantInput.IGNITION)
            },

            GSEState.PURGE: {
                required_true: (PendantInput.SYSTEM_ACTIVE, PendantInput.FILL_MODE, PendantInput.PURGE),
                required_false: (PendantInput.E_STOP,),
                nonsense_to_be_true: (PendantInput.N2O, PendantInput.ARMED, PendantInput.O2, PendantInput.IGNITION)
            },

            GSEState.O2: {
                required_true: (PendantInput.SYSTEM_ACTIVE, PendantInput.ARMED, PendantInput.O2),
                required_false: (PendantInput.E_STOP,),
                nonsense_to_be_true: (PendantInput.FILL_MODE, PendantInput.N2O, PendantInput.PURGE)
            },

            GSEState.IGNITION: {
                required_true: (PendantInput.SYSTEM_ACTIVE, PendantInput.ARMED, PendantInput.IGNITION),
                required_false: (PendantInput.E_STOP,),
                nonsense_to_be_true: (PendantInput.FILL_MODE, PendantInput.N2O, PendantInput.PURGE)
            },

            GSEState.F9: {
                required_true: (PendantInput.SYSTEM_ACTIVE, PendantInput.F9),
                required_false: (),
                nonsense_to_be_true: ()
            },

            GSEState.F10: {
                required_true: (PendantInput.SYSTEM_ACTIVE, PendantInput.F10),
                required_false: (),
                nonsense_to_be_true: ()
            },

            GSEState.F11: {
                required_true: (PendantInput.SYSTEM_ACTIVE, PendantInput.F11),
                required_false: (),
                nonsense_to_be_true: ()
            },

            GSEState.F12: {
                required_true: (PendantInput.SYSTEM_ACTIVE, PendantInput.F12),
                required_false: (),
                nonsense_to_be_true: ()
            },
        }
        # fmt: on

        gse_state_dict: dict[GSEState, bool] = {}

        # check conditions
        for state in conditions:
            required_true_conditions = conditions[state][required_true]
            required_false_conditions = conditions[state][required_false]
            nonsense_conditions = conditions[state][nonsense_to_be_true]

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
                        slogger.critical(
                            f"Impossible Condition detected for {state}: {nonsense}. This indicates a hardware issue with the pendant, please halt operations."
                        )
                        return self.FALLBACK_GSE_STATES_DICT_SYS_ON

            gse_state_dict[state] = state_is_true

        return gse_state_dict

    @staticmethod
    def get_fallback_table() -> "PendantState":
        return PendantState(PendantState.FALLBACK_PENDANT_STATES_DICT)

    @override
    def __str__(self):
        gse_states = self.get_gse_states()
        key_col_width = max([len(key) for key, _ in gse_states.items()])
        print(key_col_width)

        output = "\033[1mPendant States: \033[0m\n"
        output += "".join(
            [
                f"{key: <{key_col_width}}: {'[X]' if value else '[ ]'}\n"
                for key, value in self.states.items()
            ]
        )
        output += "\n\033[1mGSE States: \033[0m\n"
        output += "".join(
            [
                f"{key: <{key_col_width}}: {'[X]' if value else '[ ]'}\n"
                for key, value in gse_states.items()
            ]
        )
        return output

    @override
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

    @override
    def __eq__(self, other: object):
        if not isinstance(other, PendantState):
            return NotImplemented
        return self.states == other.states
