import logging
import cli.process as process

# TODO: Implement logging


class IgnoreWebMessagesFilter(logging.Filter):
    """Filter to exclude unneeded web messages"""

    def filter(self, record: logging.LogRecord) -> bool:
        return "GET" not in record.getMessage()


def start_frontend_webserver(logger: logging.Logger, performance_logging:process.RunningProcess):
    SERVICE_NAME = "frontend_webserver"
    try:
        frontend_config = config.get_config()["frontend"]
        http_host = frontend_config.get("http_host")
        http_port = frontend_config.get("http_port")
        ws_host = frontend_config.get("ws_host")
        ws_port = frontend_config.get("ws_port")

        FRONTEND_COMMAND = [
            "flask",
            "-A",
            "frontend.server",
            "run",
            f"--host={http_host}",
            f"--port={http_port}",
        ]

        logger.debug(f"Starting {SERVICE_NAME} module with: {FRONTEND_COMMAND}")
        logger.debug(
            f"{SERVICE_NAME} listening on ws://{ws_host}:{ws_port} for packets"
        )

        frontend_process = process.LoggedSubProcess(
            FRONTEND_COMMAND, name=SERVICE_NAME, parse_output=False
        )
        frontend_process._parent_logger.addFilter(IgnoreWebMessagesFilter())
        frontend_process.start()
        performance_logging.AddNewProcess(frontend_process)

    except Exception as e:
        logger.error(f"An error occurred while starting {SERVICE_NAME}: {e}")
        return None, None
