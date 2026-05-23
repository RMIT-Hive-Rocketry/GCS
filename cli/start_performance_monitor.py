import logging
from cli import process
import os
import sys


def start_performance_monitor(
    logger: logging.Logger,
    performance_logging: process.RunningProcess,
    start_time: float,
) -> None:
    service_name = "performance_monitor"
    try:
        assembled_process_list = [
            process_data.GetCombined()
            for process_data in performance_logging.GetAllProcessInfo()
        ]

        start_command = [
            sys.executable,
            "-u",
            os.path.join("backend", "performance_monitor.py"),
            "--start-time",
            str(start_time),
            "--running-services",
            str(assembled_process_list),
        ]

        logger.debug(f"Starting {service_name} module with: {start_command}")

        # Set PYTHONPATH to the project root to ensure imports work correctly.
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        performance_monitor_process = process.LoggedSubProcess(
            start_command,
            name=service_name,
            parse_output=True,
            env=env,
        )
        performance_monitor_process.start()

    except Exception as e:
        logger.error(f"An error occurred while starting {service_name}: {e}")
        return
