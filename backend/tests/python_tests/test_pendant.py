from typing_extensions import override
from backend.includes_python.devices.control_device import ControlDevice
from backend.includes_python.devices.pendant_state import (
    PendantState,
    PendantInput,
)
from typing import Never


class ExampleControlDevice(ControlDevice):
    @override
    def _setup_device(self) -> None:
        pass

    @override
    def _update_state_table(self) -> None:
        # simulate not getting packets
        pass

    @override
    def cleanup(self) -> None:
        return super().cleanup()


def test_control_device() -> None:
    device = ExampleControlDevice()

    # if _update_state_table returns nothing then we should get get_fallback_table
    assert device.get_state_table() == PendantState.get_fallback_table()

    def raise_exception(self) -> Never:
        raise RuntimeError("test")

    device._update_state_table = raise_exception

    # if it throws an error we should get_fallback_table
    assert device.get_state_table() == PendantState.get_fallback_table()

    def estop_true(self: ExampleControlDevice) -> None:
        estop_true_state = {
            PendantInput.SYSTEM_ACTIVE: True,
            PendantInput.E_STOP: True,
            PendantInput.FILL_MODE: True,
            PendantInput.ARMED: False,
            PendantInput.N2O: True,
            PendantInput.PURGE: False,
            PendantInput.O2: False,
            PendantInput.IGNITION: False,
        }
        self.state_table = PendantState(estop_true_state)

    device._update_state_table = estop_true

    assert device.get_state_table() == PendantState.get_fallback_table()
    assert (
        device.get_state_table().get_gse_states()
        == PendantState.get_fallback_table().get_gse_states()
    )


def test_control_device_manager() -> None:
    pass
