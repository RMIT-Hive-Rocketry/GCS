from backend.includes_python.devices.rpi_gpio_device import RPI_GPIO_Device
import backend.includes_python.service_helper as service_helper


def main():
    controller = RPI_GPIO_Device()
    last_state = None
    updates = 0
    while not service_helper.time_to_stop():
        states = controller.get_state_table()
        if states != last_state:
            updates += 1
            print(f"===== UPDATE [{updates}] =====")
            print(states)
        last_state = states


if __name__ == "__main__":
    main()
