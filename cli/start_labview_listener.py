import logging
from cli import process
import os
import sys


def start_labview_listener(
    logger: logging.Logger, performance_logging: process.RunningProcess = None
) -> None:
    service_name = "labview_listener"
    try:
        start_command = [
            sys.executable,
            "-u",
            os.path.join("backend", "labview_listener.py"),
        ]

        logger.debug(f"Starting {service_name} module with: {start_command}")

        # Set PYTHONPATH to the project root to ensure imports work correctly.
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        labview_process = process.LoggedSubProcess(
            start_command,
            name=service_name,
            env=env,
            parse_output=True,
        )
        labview_process.start()
        if performance_logging is not None:
            performance_logging.AddNewProcess(labview_process)

    except Exception as e:
        logger.error(f"An error occurred while starting {service_name}: {e}")
        return
