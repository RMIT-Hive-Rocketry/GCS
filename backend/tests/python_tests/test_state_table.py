from backend.includes_python.devices.state_table import StateTable2, PendantInput, GSEState

def test_eq_and_constructor():
    table_1 = StateTable2({})
    table_2 = StateTable2.get_fallback_table()

    assert table_1 == table_2

    table_1 = StateTable2({
        PendantInput.SYSTEM_ACTIVE: True,
        PendantInput.E_STOP: True,
        PendantInput.FILL_MODE: True
    })
    table_2 = StateTable2({
        PendantInput.SYSTEM_ACTIVE: True,
        PendantInput.E_STOP: True,
        PendantInput.FILL_MODE: True
    })

    assert table_1 == table_2

def test_repr():
    table_1 = StateTable2.get_fallback_table()

    assert table_1 == eval(repr(table_1))

