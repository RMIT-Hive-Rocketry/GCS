import logging
import cli.proccess as process
import os

def start_dummy_service(logger: logging.Logger):
    SERVICE_NAME = "dummy_service"
    try:

        API_SERVICE_COMMAND = [
            "python3",
            "-u",
            os.path.join("backend", "dummy_service.py"),
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

    except Exception as e:
        logger.error(
            f"An error occurred while starting the rocket {SERVICE_NAME} {e}"
        )
        return None, None