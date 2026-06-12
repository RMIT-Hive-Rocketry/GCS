import logging
from cli import process
import os
import sys


def start_simulator(
    logger: logging.Logger, device: str
) -> tuple[None, None] | None:
    service_name = "simulator"
    try:

        simulator_command = [
            sys.executable,
            "-u",
            os.path.join("backend", "simulation", "run_simulation.py"),
            "--device-rocket",
            device,
        ]

        logger.debug(
            f"Starting {service_name} module with: {simulator_command}"
        )

        # Set PYTHONPATH to the project root to ensure imports work correctly.
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        emulator_process = process.LoggedSubProcess(
            simulator_command,
            name=service_name,
            parse_output=True,
            env=env,
        )
        emulator_process.start()

    except Exception as e:
        logger.error(f"An error occurred while starting {service_name}: {e}")
        return None, None
