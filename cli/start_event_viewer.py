import logging
import cli.process as process
import os


class EventViewerSubprocess(process.LoggedSubProcess):
    """Subclass of LoggedSubProcess with a stop condition for callbacks."""

    def _update_callback_condition(self) -> bool:
        if self._callback_hits >= 1:
            self._logger_adapter.debug(
                "Stopping build callbacks for this process"
            )
            return True
        return False


def successful_event_viewer_start_callback(
    line: str, _stream_name: str
) -> bool:
    """Check if the event viewer has started successfully"""

    return "Listening for messages..." in line


def start_event_viewer(
    logger: logging.Logger, socket_path: str, file_logging_enabled: bool
) -> tuple[None, None] | None:
    service_name = "event viewer"
    try:

        event_viewer_command = [
            "python3",
            os.path.join("backend", "event_viewer.py"),
            "-u",
            "--socket-path",
            socket_path,
        ]

        if file_logging_enabled:
            event_viewer_command.append("--no-log")

        logger.debug(f"Starting {service_name} with: {event_viewer_command}")

        # Set PYTHONPATH to the project root to ensure imports work correctly.
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        event_viewer_process = EventViewerSubprocess(
            event_viewer_command, name=service_name, env=env, parse_output=True
        )

        event_viewer_process.register_callback(
            successful_event_viewer_start_callback
        )

        event_viewer_process.start()

        finished = False
        while not finished:
            finished = event_viewer_process.get_parsed_data()

        logger.info(f"{service_name} started successfully")

    except Exception as e:
        logger.error(f"An error occurred while starting {service_name}: {e}")
        return None, None
