from backend.includes_python.devices.pygame_devices import (
    HybridPygamePendant,
)
import backend.includes_python.service_helper as service_helper

import faulthandler
import signal

faulthandler.enable(all_threads=True)
# Optional: dump traceback on SIGUSR1 (mac: kill -USR1 <pid>)
faulthandler.register(signal.SIGUSR1, all_threads=True)


def main() -> None:
    controller = HybridPygamePendant()  # ThrustmasterAirbusFlightStick()
    last_state = None
    updates = 0
    while not service_helper.time_to_stop():
        states = controller.get_state_table()
        if states != last_state:
            updates += 1
            print(f"===== UPDATE [{updates}] =====")
            print(repr(states))
        last_state = states

    print("service done")


if __name__ == "__main__":
    main()
