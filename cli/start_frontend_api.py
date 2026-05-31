import logging
from cli import process
import os
import sys


def start_frontend_api(
    logger: logging.Logger,
    sub_socket_path: str,
    performance_logging: process.RunningProcess = None,
) -> None:
    service_name = "frontend_api"
    try:

        api_service_command = [
            sys.executable,
            "-u",
            os.path.join("backend", "frontend_api.py"),
            "--socket-path",
            SUB_SOCKET_PATH,
        ]

        logger.debug(
            f"Starting {SERVICE_NAME} module with: {API_SERVICE_COMMAND}"
        )

        # Set PYTHONPATH to the project root to ensure imports work correctly.
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        api_process = process.LoggedSubProcess(
            API_SERVICE_COMMAND, name=SERVICE_NAME, env=env, parse_output=True
        )
        api_process.start()
        if performance_logging is not None:
            performance_logging.AddNewProcess(api_process)

    except Exception as e:
        logger.error(
            f"An error occurred while starting the rocket {SERVICE_NAME} {e}"
        )
        return None, None
