import logging
import cli.process as process

# TODO: Implement logging


class IgnoreWebMessagesFilter(logging.Filter):
    """Filter to exclude unneeded web messages"""

    def filter(self, record: logging.LogRecord) -> bool:
        return "GET" not in record.getMessage()


def start_frontend_webserver(logger: logging.Logger):
    SERVICE_NAME = "frontend_webserver"
    try:
        FRONTEND_COMMAND = [
            "flask",
            "-A",
            "frontend.server",
            "run",
            "--host=0.0.0.0",
            "--port=8008",
        ]

        logger.debug(f"Starting {SERVICE_NAME} module with: {FRONTEND_COMMAND}")

        frontend_process = process.LoggedSubProcess(
            FRONTEND_COMMAND, name=SERVICE_NAME, parse_output=False
        )
        frontend_process._parent_logger.addFilter(IgnoreWebMessagesFilter())
        frontend_process.start()

    except Exception as e:
        logger.error(f"An error occurred while starting {SERVICE_NAME}: {e}")
        return None, None
