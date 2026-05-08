import logging
import cli.process as process
import os
import sys


def start_frontend_api(
    logger: logging.Logger,
    performance_logging: process.RunningProcess,
    sub_socket_path: str,
) -> None:
    service_name = "frontend_api"
    try:

        api_service_command = [
            sys.executable,
            "-u",
            os.path.join("backend", "frontend_api.py"),
            "--socket-path",
            sub_socket_path,
        ]

        logger.debug(
            f"Starting {service_name} module with: {api_service_command}"
        )

        # Set PYTHONPATH to the project root to ensure imports work correctly.
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        api_process = process.LoggedSubProcess(
            api_service_command, name=service_name, env=env, parse_output=True
        )
        api_process.start()
        performance_logging.AddNewProcess(api_process)

    except Exception as e:
        logger.error(
            f"An error occurred while starting the rocket {service_name} {e}"
        )
        return None, None
