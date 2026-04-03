import logging
from config.config import get_config
import time
from typing import Optional
import os
import re
import zmq
from datetime import datetime
import backend.includes_python.service_helper as service_helper

# Capture application start time (initialized in `initialise()`)
APP_START_TIME: Optional[float] = None

# When False, use short prefixes on console (set in initialise() from config)
DETAILED_LOGGING_PREFIX: bool = True

# log level (between INFO (20) and WARNING (30))
SUCCESS_LEVEL_NUM = 25
SECRET_LEVEL_NUM = 35
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")
logging.addLevelName(SECRET_LEVEL_NUM, "SECRET")

LOG_MAPPING = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "SECRET": SECRET_LEVEL_NUM,
    "SUCCESS": SUCCESS_LEVEL_NUM,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class CustomFormatter(logging.Formatter):
    """Logging formatter from https://stackoverflow.com/a/56944256/14141223"""
    DARK_YELLOW = "\x1b[33;20m"
    GREY = "\x1b[38;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    GREEN = "\x1b[32;20m"
    RESET = "\x1b[0m"
    FORMAT = "[%(levelname)-7s] %(post_start_s)5s s | %(subprocess_name)s: %(message)s"
    FORMAT_SHORT = "%(levelname_short)s %(post_start_s)ss %(subprocess_name)s | %(message)s"

    LEVEL_SHORT = {
        logging.DEBUG: "D",
        logging.INFO: "I",
        SECRET_LEVEL_NUM: "X",
        SUCCESS_LEVEL_NUM: "S",
        logging.WARNING: "W",
        logging.ERROR: "E",
        logging.CRITICAL: "C",
    }

    COLORS = {
        logging.DEBUG: GREY,
        logging.INFO: GREY,
        SECRET_LEVEL_NUM: DARK_YELLOW,
        SUCCESS_LEVEL_NUM: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED,
    }

    def __init__(self, detailed_prefix: bool = True):
        super().__init__()
        self.detailed_prefix = detailed_prefix

    def format(self, record):
        if not hasattr(record, "subprocess_name"):
            record.subprocess_name = ""  # Default empty value
        if APP_START_TIME is None:
            record.post_start_s = "0000.000"
        else:
            elapsed_s = time.perf_counter() - APP_START_TIME
            if self.detailed_prefix:
                record.post_start_s = f"{elapsed_s:09.3f}"
            else:
                record.post_start_s = f"{elapsed_s:06.2f}"
        if not self.detailed_prefix:
            record.levelname_short = self.LEVEL_SHORT.get(
                record.levelno, record.levelname[0] if record.levelname else "?"
            )
        format_str = self.FORMAT if self.detailed_prefix else self.FORMAT_SHORT
        color = self.COLORS.get(record.levelno, self.GREY)
        log_fmt = color + format_str + self.RESET
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class PlainFormatter(CustomFormatter):
    """A formatter that strips ANSI control characters for clean log files"""

    def __init__(self, detailed_prefix: bool = True):
        super().__init__(detailed_prefix=detailed_prefix)

    def format(self, record):
        # First format with the parent formatter that adds colors
        formatted_message = super().format(record)
        # Strip ANSI escape sequences using regex
        ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
        return ansi_escape.sub("", formatted_message)

class Logs_Loopback(logging.Handler):
    """A Logging handler that pushes all logs to the frountend api using ZMQ"""

    def __init__(self):
        super().__init__()
        self.buffer = []

        context = zmq.Context()

        # Wait LINGER_TIME_MS before giving up on push request
        LINGER_TIME_MS = 300

        # path to the socket read by frontend api
        FRONTEND_SOCKET_PATH = os.path.abspath(
            os.path.join(os.path.sep, "tmp", "gcs_logging_frontend_pull.sock")
        )

        self.frontend_push_socket = context.socket(zmq.PUSH)
        self.frontend_push_socket.setsockopt(zmq.LINGER, LINGER_TIME_MS)
        self.frontend_push_socket.connect(f"ipc://{FRONTEND_SOCKET_PATH}")

        # Regex pattern to match ANSI escape sequences
        self.ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')


    def emit(self, record):
        if service_helper.time_to_stop():
            # if stop signal given close socket and clean up handler
            self.frontend_push_socket.close()

        if(record.levelname =="SECRET"):
            return
        
        # Append new log
        try:
            # filter out ANSI from chars put in earlier in stream
            raw_message = record.getMessage()
            clean_message = self.ANSI_ESCAPE.sub('', raw_message)

            timestamp = datetime.fromtimestamp(record.created).isoformat()
            log_entry = [timestamp, record.levelname, clean_message]

            self.buffer.append(log_entry)

        except Exception as ex:
            
            # catch errors within the packet gen in case of malformed data and drop the packet quitely to avoid issues with cascade
            pass

        try:
            # push new logs to socket to frontend.api and clear message buffer
            self.frontend_push_socket.send_json(self.buffer, flags=zmq.NOBLOCK)
            self.buffer.clear()

        except Exception as ex:
            # Safety catch for unexpected exceptions however logging this will cause issues maybe a cascade cause log will cause more errors
            pass



                


def create_handler(
    LEVEL: int = logging.DEBUG,
    detailed_prefix: bool = True,
) -> logging.StreamHandler:
    """Create console handler with specified level and prefix style."""
    ch = logging.StreamHandler()
    ch.setLevel(LEVEL)
    ch.setFormatter(CustomFormatter(detailed_prefix=detailed_prefix))
    return ch


def create_file_handler(log_file_path: str) -> logging.FileHandler:
    """Create file handler; always uses detailed prefix for full log files."""
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    fh = logging.FileHandler(log_file_path)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(PlainFormatter(detailed_prefix=True))
    return fh

def create_interscript_comms_handler(LEVEL: int = logging.INFO)  -> logging.StreamHandler:
    """Create Log Handler to pass logs to the frontend"""
    fh = Logs_Loopback()
    fh.setLevel(LEVEL)
    return fh

def initialise():
    """One time logging setup run as soon as the program starts"""

    global APP_START_TIME, DETAILED_LOGGING_PREFIX
    APP_START_TIME = time.perf_counter()

    logger = logging.getLogger("rocket")
    if logger.hasHandlers():
        # Clear existing handlers to avoid duplicates
        logger.warning(
            "Logger has been initialised before. Stop intialising it again please"
        )
        logger.handlers.clear()

    config = get_config()
    LOG_LEVEL = config["logging"]["level"].strip()
    LOG_LEVEL_FRONT = config["logging"]["level_front"].strip()
    detailed_prefix_str = (
        config["logging"].get("detailed_logging_prefix", "true").strip().lower()
    )
    DETAILED_LOGGING_PREFIX = detailed_prefix_str == "true"

    # Get log file path from config or use default
    LOG_DIR_PATH = config["logging"]["cli_log_dir"].strip()
    log_filename = f"cli_{time.strftime('%Y%m%d_%H%M%S')}.log"
    log_file_path = os.path.join(LOG_DIR_PATH, log_filename)


    LOG_LEVEL_OBJECT = LOG_MAPPING.get(LOG_LEVEL, logging.INFO)
    logger.setLevel(logging.DEBUG)

    logger.addHandler(
        create_handler(
            LOG_LEVEL_OBJECT, detailed_prefix=DETAILED_LOGGING_PREFIX
        )
    )
    # Always debug
    logger.addHandler(create_file_handler(log_file_path))
    logger.addHandler(create_interscript_comms_handler(LOG_LEVEL_FRONT))

    return logger


def success(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kwargs)

def secret(self, message, *args, **kwargs):
    if self.isEnabledFor(SECRET_LEVEL_NUM):
        self._log(SECRET_LEVEL_NUM, message, args, **kwargs)


logging.Logger.success = success
logging.Logger.secret = secret


def adapter_success(self, message, *args, **kwargs):
    self.log(SUCCESS_LEVEL_NUM, message, *args, **kwargs)

def adapter_secret(self, message, *args, **kwargs):
    self.log(SECRET_LEVEL_NUM, message, *args, **kwargs)

logging.LoggerAdapter.success = adapter_success
logging.LoggerAdapter.secret = adapter_secret

def set_console_log_level(level_name: str):
    """
    Set the log level of the console handler at runtime.

    Args:
        level_name: Name of the log level (e.g., 'DEBUG', 'INFO', 'WARNING')
    """
    logger = logging.getLogger("rocket")

    # Convert level name to level number
    if level_name in LOG_MAPPING:
        level = LOG_MAPPING[level_name]
    else:
        logger.error(f"Invalid log level: {level_name}. Using INFO.")
        level = logging.INFO

    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.FileHandler
        ):
            handler.setLevel(level)
            logger.debug(
                f"Console log level set to {level_name} post intialisation"
            )
            return

    logger.warning("No console handler found")


def set_console_low_detail(low_detail: bool):
    """
    Set console prefix detail at runtime to low
    """
    logger = logging.getLogger("rocket")

    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.FileHandler
        ):
            handler.setFormatter(
                CustomFormatter(detailed_prefix=not low_detail)
            )
            global DETAILED_LOGGING_PREFIX
            DETAILED_LOGGING_PREFIX = not low_detail
            return

    logger.warning("No console handler found")
