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


def test_correct_states():
    # list of all possible correct states
    # also tests if filling in non existant states as false works

    global all_correct_states

    for test_pendant_states, expected_gse_states in all_correct_states.items():
        pendant_state_dict = {s: True for s in test_pendant_states}

        expected_gse_state_dict = {
            s: s in expected_gse_states for s in GSEState
        }

        assert (
            PendantState(pendant_state_dict).get_gse_states()
            == expected_gse_state_dict
        )


def test_invalid_key_raises():
    # passing an invalid key should raise TypeError
    import pytest

    with pytest.raises(TypeError):
        PendantState({"NOT_A_REAL_INPUT": True})  # type: ignore


def test_all_state():
    # check that for every other possible state, they are either all off (for estop) or the fallback table

    global all_correct_states

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


def test_explicit_false_same_as_omitting():
    # explicitly setting a key to False should produce the same state as omitting it
    with_false = PendantState(
        {PendantInput.SYSTEM_ACTIVE: True, PendantInput.FILL_MODE: False}
    )
    without_key = PendantState({PendantInput.SYSTEM_ACTIVE: True})
    assert with_false == without_key


def test_partial_constructor_fills_all_keys():
    # all PendantInput keys should be present after constructing from a subset
    state = PendantState({PendantInput.SYSTEM_ACTIVE: True})
    assert set(state.states.keys()) == set(PendantInput)


def test_e_stop_alone_gives_all_false():
    # E_STOP with no other inputs → all GSE states False
    state = PendantState({PendantInput.E_STOP: True})
    assert state.get_gse_states() == {s: False for s in GSEState}


def test_e_stop_overrides_system_active():
    # E_STOP should suppress SYSTEM_ACTIVE in GSE output
    state = PendantState(
        {PendantInput.SYSTEM_ACTIVE: True, PendantInput.E_STOP: True}
    )
    assert state.get_gse_states() == {s: False for s in GSEState}


def test_fallback_table_matches_constant():
    # get_fallback_table() GSE output should match FALLBACK_GSE_STATES_DICT
    assert (
        PendantState.get_fallback_table().get_gse_states()
        == PendantState.FALLBACK_GSE_STATES_DICT
    )


def test_eq_non_pendant_state():
    # __eq__ with a non-PendantState should return NotImplemented (not crash)
    state = PendantState({})
    result = state.__eq__("not a pendant state")
    assert result is NotImplemented
