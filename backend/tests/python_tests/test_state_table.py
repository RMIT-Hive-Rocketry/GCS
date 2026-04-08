from backend.includes_python.devices.pendant_state import (
    PendantState,
    PendantInput,
    GSEState,
)
from typing import List, Dict, Tuple
from dataclasses import dataclass


def test_eq_and_constructor():
    table_1 = PendantState({})
    table_2 = PendantState.get_fallback_table()

    assert table_1 == table_2

    table_1 = PendantState(
        {
            PendantInput.SYSTEM_ACTIVE: True,
            PendantInput.E_STOP: True,
            PendantInput.FILL_MODE: True,
        }
    )
    table_2 = PendantState(
        {
            PendantInput.SYSTEM_ACTIVE: True,
            PendantInput.E_STOP: True,
            PendantInput.FILL_MODE: True,
        }
    )

    assert table_1 == table_2


def test_repr():
    table_1 = PendantState.get_fallback_table()

    assert table_1 == eval(repr(table_1))


@dataclass
class PendantStateTestCase:
    # important stuff
    SYSTEM_ACTIVE: bool
    E_STOP: bool

    # first toggle
    FILL_MODE: bool
    ARMED: bool

    # second toggle
    N2O: bool
    PURGE: bool

    # buttons
    O2: bool
    IGNITION: bool

    def to_dict(self) -> Dict[PendantInput, bool]:
        return {
            # important stuff
            PendantInput.SYSTEM_ACTIVE: self.SYSTEM_ACTIVE,
            PendantInput.E_STOP: self.E_STOP,
            # first toggle
            PendantInput.FILL_MODE: self.FILL_MODE,
            PendantInput.ARMED: self.ARMED,
            # second toggle
            PendantInput.N2O: self.N2O,
            PendantInput.PURGE: self.PURGE,
            # buttons
            PendantInput.O2: self.O2,
            PendantInput.IGNITION: self.IGNITION,
        }


@dataclass
class ExpectedGSEStatesTestCase:
    # important stuff
    SYSTEM_ACTIVE: bool

    # first toggle
    FILL_MODE: bool
    ARMED: bool

    # second toggle
    N2O: bool
    NEUTRAL: bool
    PURGE: bool

    # buttons
    O2: bool
    IGNITION: bool

    def to_dict(self) -> Dict[GSEState, bool]:
        return {
            # important stuff
            GSEState.SYSTEM_ACTIVE: self.SYSTEM_ACTIVE,
            # first toggle
            GSEState.FILL_MODE: self.FILL_MODE,
            GSEState.ARMED: self.ARMED,
            # second toggle
            GSEState.N2O: self.N2O,
            GSEState.NEUTRAL: self.NEUTRAL,
            GSEState.PURGE: self.PURGE,
            # buttons
            GSEState.O2: self.O2,
            GSEState.IGNITION: self.IGNITION,
        }


def test_all_correct_states():
    correct_test_cases: List[
        Tuple[PendantStateTestCase, ExpectedGSEStatesTestCase]
    ] = [
        # SYSTEM OFF
        (
            PendantStateTestCase(
                False, False, False, False, False, False, False, False
            ),
            ExpectedGSEStatesTestCase(
                False, False, False, False, False, False, False, False
            ),
        ),
        # E_STOP
        (
            PendantStateTestCase(
                True, True, False, True, False, False, True, True
            ),
            ExpectedGSEStatesTestCase(
                False, False, False, False, False, False, False, False
            ),
        ),
        # STANDBY
        (
            PendantStateTestCase(
                True, False, False, False, False, False, False, False
            ),
            ExpectedGSEStatesTestCase(
                True, False, False, False, False, False, False, False
            ),
        ),
        # FILL_MODE
        (
            PendantStateTestCase(
                True, False, True, False, False, False, False, False
            ),
            ExpectedGSEStatesTestCase(
                True, True, False, False, True, False, False, False
            ),
        ),
        (
            PendantStateTestCase(
                True, False, True, False, True, False, False, False
            ),
            ExpectedGSEStatesTestCase(
                True, True, False, True, False, False, False, False
            ),
        ),
        (
            PendantStateTestCase(
                True, False, True, False, False, True, False, False
            ),
            ExpectedGSEStatesTestCase(
                True, True, False, False, False, True, False, False
            ),
        ),
        # ARMED
        (
            PendantStateTestCase(
                True, False, False, True, False, False, False, False
            ),
            ExpectedGSEStatesTestCase(
                True, False, True, False, False, False, False, False
            ),
        ),
        (
            PendantStateTestCase(
                True, False, False, True, False, False, True, False
            ),
            ExpectedGSEStatesTestCase(
                True, False, True, False, False, False, True, False
            ),
        ),
        (
            PendantStateTestCase(
                True, False, False, True, False, False, False, True
            ),
            ExpectedGSEStatesTestCase(
                True, False, True, False, False, False, False, True
            ),
        ),
        (
            PendantStateTestCase(
                True, False, False, True, False, False, True, True
            ),
            ExpectedGSEStatesTestCase(
                True, False, True, False, False, False, True, True
            ),
        ),
    ]

    for case in correct_test_cases:
        table = PendantState(case[0].to_dict())
        assert table.get_gse_states() == case[1].to_dict()


def test_nonsense_states():
    nonsense_states: List[PendantStateTestCase] = [
        PendantStateTestCase(
            True, False, True, True, False, False, False, False
        ),  # FILL_MODE and ARMED
        PendantStateTestCase(
            True, False, True, False, True, True, False, False
        ),  # N2O and PURGE
    ]

    for state in nonsense_states:
        table = PendantState(state.to_dict())

        assert (
            table.get_gse_states()
            == table.get_fallback_table().get_gse_states()
        )
