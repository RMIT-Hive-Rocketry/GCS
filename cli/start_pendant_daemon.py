import logging
import cli.proccess as process
import os


def start_pendant_daemon(logger: logging.Logger, performance_logging:process.RunningProcess):
    SERVICE_NAME = "pendant_daemon"
    try:

        DAEMON_COMMAND = [
            "python3",
            "-u",
            os.path.join("backend", "pendant_daemon.py"),
        ]

        logger.debug(f"Starting {SERVICE_NAME} module with: {DAEMON_COMMAND}")

        # Set PYTHONPATH to the project root to ensure imports work correctly.
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        env["SDL_VIDEODRIVER"] = "dummy"

        api_process = process.LoggedSubProcess(
            DAEMON_COMMAND, name=SERVICE_NAME, env=env, parse_output=True
        )
        api_process.start()
        performance_logging.AddNewProcess(api_process)
        

    except Exception as e:
        logger.error(
            f"An error occurred while starting the rocket {SERVICE_NAME} {e}"
        )
        return None, None
