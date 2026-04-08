from backend.includes_python.devices.control_device import ControlDevice
from backend.includes_python.devices.control_device_manager import (
    ControlDeviceManager,
)
from backend.includes_python.devices.pendant_state import PendantState, PendantInput


class ExampleControlDevice(ControlDevice):
    def _setup_device(self):
        pass

    def _update_state_table(self) -> None:
        # simulate not getting packets
        pass

    def cleanup(self) -> None:
        return super().cleanup()


def test_control_device():
    device = ExampleControlDevice()

    # if _update_state_table retuns nothing then we should get get_fallback_table
    assert device.get_state_table() == PendantState.get_fallback_table()

    def raise_exception(self):
        raise RuntimeError("test")

    device._update_state_table = raise_exception

    # if it throws an error we should get_fallback_table
    assert device.get_state_table() == PendantState.get_fallback_table()

    def estop_true(self: ExampleControlDevice):
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
    assert device.get_state_table().get_gse_states() == PendantState.get_fallback_table().get_gse_states() 


def test_control_device_manager():
    pass
