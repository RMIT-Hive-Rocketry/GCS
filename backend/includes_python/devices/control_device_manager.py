from backend.includes_python.devices.control_device import ControlDevice
import backend.includes_python.process_logging as slogger
import config.config as config
from typing import Dict, Callable, Type

class ControlDeviceManager:
    """
    Manages the creation and storage of pendant devices
    Only ever stores one device
    imports the device at runtime because some require specialised imports such as the HID library and gpiozero library
    """

    instance: ControlDevice | None
    managed_devices: Dict[str, Callable[[], Type[ControlDevice]]]

    def __init__(self):
        self.instance = None
        self.managed_devices = {}
    
    def add_managed_device(self, name: str, import_func: Callable[[], Type[ControlDevice]]):
        self.managed_devices[name] = import_func

    def get_control_device(self) -> ControlDevice:
        if self.instance is not None:
            return self.instance

        config_dict = config.get_config()
        control_type = config_dict["hardware"]["controller"]

        if control_type in self.managed_devices:
            device_reference: Type[ControlDevice] = self.managed_devices[control_type]()
            self.instance = device_reference()
            return self.instance
        else:
            error_msg = f"Control device `{control_type}` not found"
            slogger.critical(error_msg)
            raise RuntimeError(error_msg)

if __name__ == "__main__":
    slogger.critical("How tf did this even manage to run")
    # main guard will obv never run but here is an example of intended use:

    manager = ControlDeviceManager()

    def example_import():
        from backend.includes_python.devices.control_device import ControlDevice
        return ControlDevice


    manager.add_managed_device(
        name = "example_device",
        import_func = example_import
    )

    device = manager.get_control_device()

    raise RuntimeError("How tf did this even manage to run")
