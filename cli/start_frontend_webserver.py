import logging
from cli import process
from config import config
import sys


class IgnoreWebMessagesFilter(logging.Filter):
    """Filter to exclude unneeded web messages"""

    def filter(self, record: logging.LogRecord) -> bool:
        return "GET" not in record.getMessage()


def start_frontend_webserver(
    logger: logging.Logger,
    performance_logging: process.RunningProcess | None = None,
) -> None:
    service_name = "frontend_webserver"
    try:
        frontend_config = config.get_config()["frontend"]
        http_host = frontend_config.get("http_host")
        http_port = frontend_config.get("http_port")
        ws_host = frontend_config.get("ws_host")
        ws_port = frontend_config.get("ws_port")

        frontend_command = [
            sys.executable,
            "-u",
            "-m",
            "flask",
            "-A",
            "frontend.server",
            "run",
            f"--host={http_host}",
            f"--port={http_port}",
        ]

        logger.debug(f"Starting {service_name} module with: {frontend_command}")

        # I've commented this out since the ws_host IP isn't accurate to what the host is
        # Since the config is almost always 0.0.0.0 for the host, but the clients need a specific IP
        # logger.debug(f"{service_name} listening on ws://{ws_host}:{ws_port} for packets")

        # Start frontend subprocess
        frontend_process = process.LoggedSubProcess(
            frontend_command, name=service_name, parse_output=False
        )
        frontend_process._parent_logger.addFilter(IgnoreWebMessagesFilter())
        frontend_process.start()

        # Add frontend subprocess to performance_logging
        if performance_logging is not None:
            performance_logging.AddNewProcess(frontend_process)

    except Exception as e:
        logger.error(f"An error occurred while starting {service_name}: {e}")
        return
