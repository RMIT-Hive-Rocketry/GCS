import logging
import cli.proccess as process
from typing import Tuple
import os




def start_dummy_alert(
    logger: logging.Logger
):
    SERVICE_NAME = "dummy alert"
    try:

        DUMMY_ALERT_COMMAND = [
            "python3",
            os.path.join("backend", "dummy_alert.py"),
            "-u",
        ]

        logger.debug(f"Starting {SERVICE_NAME}")

        # Set PYTHONPATH to the project root to ensure imports work correctly.
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        dummy_alert_process = process.LoggedSubProcess(
            DUMMY_ALERT_COMMAND, name=SERVICE_NAME, env=env, parse_output=True
        )

        dummy_alert_process.start()

    except Exception as e:
        logger.error(f"An error occurred while starting {SERVICE_NAME}: {e}")
        return None, None
