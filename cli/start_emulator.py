import logging
import cli.process as process
import cli.start_middleware as start_middleware


def start_fake_serial_device_emulator(
    logger: logging.Logger,
    device: str,
    interface_type: start_middleware.InterfaceType,
    experimental: bool,
    corruption: bool,
) -> None:
    service_name = "device emulator"
    try:

        emulator_command = [
            "python3",
            "-u",
            "-Xfrozen_modules=off",
            "-m",
            "backend.device_emulator",
            "--device-rocket",
            device,
            "--interface-type",
            interface_type.value,
        ]

        if experimental:
            emulator_command.append("--experimental")

        if corruption:
            emulator_command.append("--corruption")

        logger.debug(
            f"Starting {service_name} module with: {emulator_command} with interface type: {interface_type}"
        )

        emulator_process = process.LoggedSubProcess(
            emulator_command, name=service_name, parse_output=True
        )
        emulator_process.start()

    except Exception as e:
        logger.error(f"An error occurred while starting {service_name}: {e}")
        raise
