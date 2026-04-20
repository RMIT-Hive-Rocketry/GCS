from backend.includes_python.devices.pendant_state import (
    PendantState,
    PendantInput,
    GSEState,
)
from typing import List, Dict, Tuple
import itertools


def test_eq_and_constructor():
    table_1 = PendantState({})
    table_2 = PendantState({})

    assert table_1 == table_2
    assert not table_1 != table_2

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
    assert not table_1 != table_2

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


def test_repr():
    table_1 = PendantState.get_fallback_table()

    assert table_1 == eval(repr(table_1))


def test_all_states():
    # list of all possible correct states
    # also tests if filling in non existant states as false works

    # fmt: off
    all_correct_states: Dict[Tuple[PendantInput, ...], Tuple[GSEState, ...]] = {
        (): (),
        (PendantInput.SYSTEM_ACTIVE,): (GSEState.SYSTEM_ACTIVE,),
        (PendantInput.SYSTEM_ACTIVE, PendantInput.FILL_MODE): (GSEState.SYSTEM_ACTIVE, GSEState.FILL_MODE, GSEState.NEUTRAL),
        (PendantInput.SYSTEM_ACTIVE, PendantInput.FILL_MODE, PendantInput.N2O): (GSEState.SYSTEM_ACTIVE, GSEState.FILL_MODE, GSEState.N2O),
        (PendantInput.SYSTEM_ACTIVE, PendantInput.FILL_MODE, PendantInput.PURGE): (GSEState.SYSTEM_ACTIVE, GSEState.FILL_MODE, GSEState.PURGE),

        (PendantInput.SYSTEM_ACTIVE, PendantInput.ARMED): (GSEState.SYSTEM_ACTIVE, GSEState.ARMED),
        (PendantInput.SYSTEM_ACTIVE, PendantInput.ARMED, PendantInput.O2): (GSEState.SYSTEM_ACTIVE, GSEState.ARMED, GSEState.O2),
        (PendantInput.SYSTEM_ACTIVE, PendantInput.ARMED, PendantInput.IGNITION): (GSEState.SYSTEM_ACTIVE, GSEState.ARMED, GSEState.IGNITION),
        (PendantInput.SYSTEM_ACTIVE, PendantInput.ARMED, PendantInput.O2, PendantInput.IGNITION): (GSEState.SYSTEM_ACTIVE, GSEState.ARMED, GSEState.O2, GSEState.IGNITION),
    }
    # fmt: on

    for test_pendant_states, expected_gse_states in all_correct_states.items():
        pendant_state_dict = {s: True for s in test_pendant_states}

        expected_gse_state_dict = {
            s: s in expected_gse_states for s in GSEState
        }

        assert (
            PendantState(pendant_state_dict).get_gse_states()
            == expected_gse_state_dict
        )

    # check that for every other possible state, they are either all off (for estop) or the fallback table
    # https://stackoverflow.com/questions/464864/how-to-get-all-possible-2n-combinations-of-a-list-s-elements-of-any-length
    count = 0
    for L in range(len(PendantInput) + 1):
        for test_pendant_states in itertools.combinations(PendantInput, L):
            count += 1

            if test_pendant_states in all_correct_states:
                continue

            pendant_state_dict = {s: True for s in test_pendant_states}

            gse_state = PendantState(pendant_state_dict).get_gse_states()

            if PendantInput.E_STOP in test_pendant_states:
                assert gse_state == {s: False for s in GSEState}

            assert (
                gse_state == PendantState.get_fallback_table().get_gse_states()
                or gse_state == {s: False for s in GSEState}
            )

    # make sure we go over every permutation
    # 2^num_inputs = 2^8 = 256
    assert count == 256
