import logging
import cli.process as process
import os
import sys


def start_pendant_emulator(
    logger: logging.Logger, performance_logging: process.RunningProcess
) -> tuple[None, None] | None:
    service_name = "pendant_emulator"
    try:
        emulator_command = [
            sys.executable,
            "-u",
            os.path.join("backend", "pendant_emulator.py"),
        ]

        logger.debug(f"Starting {service_name} module with: {emulator_command}")

        # Set PYTHONPATH to the project root to ensure imports work correctly.
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        env["SDL_VIDEODRIVER"] = "dummy"

        api_process = process.LoggedSubProcess(
            emulator_command, name=service_name, env=env, parse_output=True
        )
        api_process.start()
        performance_logging.AddNewProcess(api_process)

    except Exception as e:
        logger.error(
            f"An error occurred while starting the rocket {service_name} {e}"
        )
        return None, None
