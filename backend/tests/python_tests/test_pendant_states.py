from backend.includes_python.devices.pendant_state import (
    PendantState,
    PendantInput,
    GSEState,
)
import itertools


def test_eq_and_constructor() -> None:
    table_1 = PendantState({})
    table_2 = PendantState({})

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


def test_repr() -> None:
    table_1 = PendantState.get_fallback_table()

    assert table_1 == eval(repr(table_1))


# fmt: off
all_correct_states: dict[tuple[PendantInput, ...], tuple[GSEState, ...]] = {
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


def test_correct_states() -> None:
    # list of all possible correct states
    # also tests if filling in non existent states as false works
    for test_pendant_states, expected_gse_states in all_correct_states.items():
        pendant_state_dict = dict.fromkeys(test_pendant_states, True)

        expected_gse_state_dict = {
            s: s in expected_gse_states for s in GSEState
        }

        assert (
            PendantState(pendant_state_dict).get_gse_states()
            == expected_gse_state_dict
        )


def test_invalid_key_raises() -> None:
    # passing an invalid key should raise TypeError
    import pytest  # noqa: PLC0415

    with pytest.raises(TypeError):
        PendantState({"NOT_A_REAL_INPUT": True})  # type: ignore


def test_all_state() -> None:
    # check that for every other possible state, they are either all off (for estop) or the fallback table
    # https://stackoverflow.com/questions/464864/how-to-get-all-possible-2n-combinations-of-a-list-s-elements-of-any-length
    total_permutations: int = 2 ** len(PendantInput)
    count: int = 0

    for i in range(len(PendantInput) + 1):
        for test_pendant_states in itertools.combinations(PendantInput, i):
            count += 1

            # Test correct states
            # Please note that F9, F10, F11 and F12 aren't tested in this function
            if (
                tuple(
                    x
                    for x in test_pendant_states
                    if x not in ["F9", "F10", "F11", "F12"]
                )
                in all_correct_states
            ):
                continue

            pendant_state_dict = dict.fromkeys(test_pendant_states, True)
            gse_state_dict = dict.fromkeys(GSEState, False)

            gse_state = PendantState(pendant_state_dict).get_gse_states()

            # We don't need to worry about these states
            gse_state[GSEState.F9] = False
            gse_state[GSEState.F10] = False
            gse_state[GSEState.F11] = False
            gse_state[GSEState.F12] = False

            if PendantInput.E_STOP in test_pendant_states:
                assert gse_state == gse_state_dict

            # its fine if sys is on, its only problematic if other inputs like ignition are on
            SYS_ON_STATE = {
                GSEState.SYSTEM_ACTIVE: True,
                GSEState.FILL_MODE: False,
                GSEState.ARMED: False,
                GSEState.N2O: False,
                GSEState.NEUTRAL: False,
                GSEState.PURGE: False,
                GSEState.O2: False,
                GSEState.IGNITION: False,
                GSEState.F9: False,
                GSEState.F10: False,
                GSEState.F11: False,
                GSEState.F12: False,
            }

            assert (
                gse_state == PendantState.FALLBACK_GSE_STATES_DICT
                or gse_state == PendantState.FALLBACK_GSE_STATES_DICT_SYS_ON
                or gse_state == SYS_ON_STATE
            )

    # make sure we go over every permutation
    # 2^num_inputs = 2^12 = 4096
    assert count == total_permutations


def test_explicit_false_same_as_omitting() -> None:
    # explicitly setting a key to False should produce the same state as omitting it
    with_false = PendantState(
        {PendantInput.SYSTEM_ACTIVE: True, PendantInput.FILL_MODE: False}
    )
    without_key = PendantState({PendantInput.SYSTEM_ACTIVE: True})
    assert with_false == without_key


def test_partial_constructor_fills_all_keys() -> None:
    # all PendantInput keys should be present after constructing from a subset
    state = PendantState({PendantInput.SYSTEM_ACTIVE: True})
    assert set(state.states.keys()) == set(PendantInput)


def test_e_stop_alone_gives_all_false() -> None:
    # E_STOP with no other inputs → all GSE states False
    state = PendantState({PendantInput.E_STOP: True})
    assert state.get_gse_states() == dict.fromkeys(GSEState, False)


def test_e_stop_overrides_system_active() -> None:
    # E_STOP should suppress SYSTEM_ACTIVE in GSE output
    state = PendantState(
        {PendantInput.SYSTEM_ACTIVE: True, PendantInput.E_STOP: True}
    )
    assert state.get_gse_states() == dict.fromkeys(GSEState, False)


def test_fallback_table_matches_constant() -> None:
    # get_fallback_table() GSE output should match FALLBACK_GSE_STATES_DICT
    assert (
        PendantState.get_fallback_table().get_gse_states()
        == PendantState.FALLBACK_GSE_STATES_DICT
    )


def test_eq_non_pendant_state() -> None:
    # __eq__ with a non-PendantState should return NotImplemented (not crash)
    state = PendantState({})
    result = state.__eq__("not a pendant state")
    assert result is NotImplemented
