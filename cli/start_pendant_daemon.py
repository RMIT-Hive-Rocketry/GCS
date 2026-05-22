import logging
from cli import process
import os
import sys


def start_pendant_daemon(logger: logging.Logger, performance_logging:process.RunningProcess):
    SERVICE_NAME = "pendant_daemon"
    try:

        daemon_command = [
            sys.executable,
            "-u",
            os.path.join("backend", "pendant_daemon.py"),
        ]

        logger.debug(f"Starting {service_name} module with: {daemon_command}")

        # Set PYTHONPATH to the project root to ensure imports work correctly.
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        env["SDL_VIDEODRIVER"] = "dummy"

        api_process = process.LoggedSubProcess(
            daemon_command, name=service_name, env=env, parse_output=True
        )
        api_process.start()
        performance_logging.AddNewProcess(api_process)
        

    except Exception as e:
        logger.error(
            f"An error occurred while starting the rocket {service_name} {e}"
        )
        return None, None
