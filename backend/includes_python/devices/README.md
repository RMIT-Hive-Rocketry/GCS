# Devices readme
This readme is a basic explanation of what's going on in this folder

This folder defines various classes which read inputs from control pendants, or act as control pendants.
It also has special things such as `PendantState` and `ControlDeviceManager`.

## Control Device Manager
The `ControlDeviceManager` manages control devices, where a control device is a class which either takes input from a physical device or emulates input and stores a state table (mentioned later).

it only ever stores a single instance of any control device.

`get_control_device()` manages all config stuff so you don't have to worry

to use it all you do is:
1) instantiate the `ControlDeviceManager`
2) make a function which imports your device class at runtime and returns it
3) register the device with its name and function you made
4) call `get_control_device()` on the instance of `ControlDeviceManager` you made

```
manager = ControlDeviceManager()

    def example_import():
        from backend.includes_python.devices.example_device import ExampleDevice
        return ExampleDevice


    manager.add_managed_device(
        name = "example_device",
        import_func = example_import
    )

    device = manager.get_control_device()
```

## State Table
The state table is a class which represents the state of a control device. It is error checked and has a fallback.

Don't try modify it recklessly, as it is tightly coupled with device_emulator.py and our custom SRAD networking scheme.

## Pygame Device
PygameDevice is an ABC, where children only need to define the name of the hid device and the mapping between buttons and states.

```
class HybridPygamePendant(PygameDevice):
    BUTTON_NAME_ID_MAP = {
        "SYS_ON": 0,
        "ESTOP": 5,
        "FILL_SELECTED": 6,
        "IGNITION_SELECTED": 4,
        "N2O_ACTIVE": 8,
        "PURGE_ACTIVE": 3,
        "O2_MOMENT_ACTIVE": 1,
        "IGNITION_MOMENT_ACTIVE": 2,
    }

    CONTROLLER_NAME = "DragonRise Inc. Generic USB Joystick"
```

For help getting the mapping you can use the `start Pygame input decoder` task
