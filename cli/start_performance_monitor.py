import logging
import cli.process as process
import os


def start_performance_monitor(
    logger: logging.Logger,
    performance_logging: process.RunningProcess,
    startTime,
):
    SERVICE_NAME = "performance_monitor"
    try:
        assembledProcessList = []

        for processdata in performance_logging.GetAllProcessInfo():
            assembledProcessList.append(processdata.GetCombined())

        START_COMMAND = [
            "python3",
            "-u",
            os.path.join("backend", "performance_monitor.py"),
            "--START_TIME",
            str(startTime),
            "--running_services",
            str(assembledProcessList),
        ]

        logger.debug(f"Starting {SERVICE_NAME} module with: {START_COMMAND}")

        # Set PYTHONPATH to the project root to ensure imports work correctly.
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        performance_monitor_process = process.LoggedSubProcess(
            START_COMMAND,
            name=SERVICE_NAME,
            parse_output=True,
            env=env,
        )
        performance_monitor_process.start()

    except Exception as e:
        logger.error(f"An error occurred while starting {SERVICE_NAME}: {e}")
        return None
