from backend.includes_python.devices.control_device import ControlDevice
from backend.includes_python.devices.control_device_manager import ControlDeviceManager
from backend.includes_python.devices.state_table import StateTable

class ExampleControlDevice(ControlDevice):
    def _setup_device(self):
        pass

    def _update_state_table(self) -> None:
        # simulate not getting packets
        pass

    

def test_control_device():
    device = ExampleControlDevice()

    # if _update_state_table retuns nothing then we should get get_fallback_table
    assert device.get_state_table() == StateTable.get_fallback_table()

    def raise_exception(self):
        raise RuntimeError("test")

    device._update_state_table = raise_exception

    # if it throws an error we should get_fallback_table
    assert device.get_state_table() == StateTable.get_fallback_table()

    def estop_true(self):
        estop_true_state = {
            "SYS_ON": True,
            "ESTOP": True,
            "FILL_SELECTED": True,
            "IGNITION_SELECTED": False,
            "N2O_ACTIVE": True,
            "PURGE_ACTIVE": False,
            "O2_MOMENT_ACTIVE": False,
            "IGNITION_MOMENT_ACTIVE": False,
        }
        return estop_true_state

    device._update_state_table = estop_true

    # TODO: figure out exactly what estop does
    assert True

    


def test_state_table():
    fallback_table: StateTable = StateTable.get_fallback_table()
    fallback_dict = fallback_table.get_states_dict()
    
    # fallback table should be all false
    for key in fallback_dict:
        assert not fallback_dict[key]

    
def test_control_device_manager():
    pass