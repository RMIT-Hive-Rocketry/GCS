import logging
import cli.proccess as process
import os
import enum
import config.config as config
from dataclasses import dataclass
from typing import List, Optional


class InterfaceType(enum.Enum):
    # Reference the main middleware cpp file
    UART_E5 = "UART_E5"
    TEST = "TEST"
    TEST_UART_E5 = "TEST_UART_E5"
    TCP = "TCP"


def get_interface_type(interface: Optional[str]) -> InterfaceType:
    """Get the interface type from the command line argument or config"""
    if interface is None:  # Unspecified by user
        interface = config.get_config(
        )['hardware']['interface'].strip().upper()
    else:
        interface = interface.strip().upper()

    # Convert string to InterfaceType enum
    try:
        for enum_member in InterfaceType:
            if enum_member.name == interface:
                return enum_member
        # If we get here, no matching enum value was found
        valid_types = [e.name for e in InterfaceType]
        raise ValueError(
            f"Invalid interface type: '{interface}'. Valid types are: {', '.join(valid_types)}")
    except Exception as e:
        raise ValueError(f"Invalid interface type: {interface}")


@dataclass
class MiddlewareConfig:
    """Configuration for launching the C++ middleware server.

    This wraps all the CLI-facing arguments so callers do not need to thread
    long positional parameter lists through Python.
    """

    release: bool
    interface_gse_type: InterfaceType
    device_path_gse: str
    interface_av_type: InterfaceType
    device_path_av: str
    pendant_socket_path: str = "gcs_rocket"
    web_control_socket_path: Optional[str] = None
    opt_arg: Optional[str] = None
    lora_config: Optional[dict] = None


class MiddlewareSubprocess(process.LoggedSubProcess):
    """Subclass of LoggedSubProcess with a stop condition for callbacks.
    """

    def _update_callback_condition(self) -> bool:
        if self._callback_hits >= 1:
            self._logger_adapter.debug(
                "Stopping build callbacks for this process")
            return True
        return False


def middleware_started_callback(line: str, stream_name: str):
    """Check if middleware has started"""

    if "Middleware server started successfully" in line:
        return True


def get_middleware_path(BINARY_NAME_PREFIX: str, RELEASE: bool) -> Optional[str]:
    """Check if middleware is in build/ then check if it is in root folder.
    This helps when sharing releases, but still prioritises the build/ folder.
    """

    if RELEASE:
        BUILD_DIR = "build-release"
    else:
        BUILD_DIR = "build-debug"

    # Cmake folder
    BUILD_PATH_ABS = os.path.join(os.getcwd(), BUILD_DIR)
    build_path_files = [os.path.join(BUILD_PATH_ABS, x)
                        for x in os.listdir(BUILD_PATH_ABS)]
    build_path_files = [x for x in build_path_files if os.path.isfile(x)]
    # User placed
    PROJECT_PATH_ABS = os.getcwd()
    project_root_files = [os.path.join(PROJECT_PATH_ABS, x)
                          for x in os.listdir(PROJECT_PATH_ABS)]
    project_root_files = [x for x in project_root_files if os.path.isfile(x)]

    file_matches = []
    for path in build_path_files + project_root_files:
        filename = os.path.basename(path)
        if filename.startswith(BINARY_NAME_PREFIX):
            file_matches.append(path)

    if len(file_matches) > 1:
        raise RuntimeError(
            f"Multiple middleware binaries found. Please remove or archive the extra ones: {file_matches}")
    elif len(file_matches) == 0:
        return None

    BINARY_PATH = file_matches[0]

    with open("VERSION", "r") as f:
        VERSION_STRING = f.read().strip()

    # Actual file may have build metadata in it. Substring match is fine
    if VERSION_STRING not in os.path.basename(BINARY_PATH):
        raise RuntimeError(
            f"Middleware binary version mismatch. Expected prefix: {VERSION_STRING}, found: {os.path.basename(BINARY_PATH)}. The repository branch VERSION file does not match the binary version found")

    return file_matches[0]


def build_middleware_argv(config: MiddlewareConfig, binary_path: str) -> List[str]:
    """Build argv for the middleware process (always gse + av format).

    Order: binary, gse_type, gse_path, av_type, av_path, pendant, web,
    [9 lora params if gse_type==UART_E5], [--GSE_ONLY].
    """
    if not isinstance(config.interface_gse_type, InterfaceType) or not isinstance(
        config.interface_av_type, InterfaceType
    ):
        raise ValueError(
            "interface_gse_type and interface_av_type must be InterfaceType"
        )
    argv = [
        binary_path,
        config.interface_gse_type.value,
        config.device_path_gse,
        config.interface_av_type.value,
        config.device_path_av,
        config.pendant_socket_path,
        config.web_control_socket_path,
    ]
    if config.interface_gse_type == InterfaceType.UART_E5:
        if config.lora_config is None:
            raise ValueError("UART_E5 GSE interface requires lora_config")
        argv.extend([
            config.lora_config["frequency"],
            config.lora_config["spread_factor"],
            config.lora_config["bandwidth"],
            config.lora_config["tx_preamble"],
            config.lora_config["rx_preamble"],
            config.lora_config["power"],
            config.lora_config["crc"],
            config.lora_config["iq"],
            config.lora_config["net"],
        ])
    if config.opt_arg is not None:
        argv.append(config.opt_arg)
    return argv


def start_middleware(logger: logging.Logger, config: MiddlewareConfig) -> None:

    SERVICE_NAME = "middleware_server"
    if config.web_control_socket_path is None:
        config.web_control_socket_path = os.path.abspath(
            os.path.join(os.path.sep, "tmp", "gcs_rocket_web_pull.sock")
        )
    try:
        BINARY_NAME = "middleware_release" if config.release else "middleware_debug"
        MIDDLEWARE_BINARY_PATH = get_middleware_path(BINARY_NAME, config.release)
        if MIDDLEWARE_BINARY_PATH is None:
            logger.debug(f"WORKING DIRECTORY: {os.getcwd()}")
            raise FileNotFoundError(
                f"Could not find {SERVICE_NAME} binary ({BINARY_NAME}) in build folders or root folder. Please run $ bash scripts/release.sh")

        middleware_command = build_middleware_argv(config, MIDDLEWARE_BINARY_PATH)

        logger.debug(f"Starting {SERVICE_NAME} with: {middleware_command}")

        middleware_process = MiddlewareSubprocess(
            middleware_command,
            name=SERVICE_NAME,
            parse_output=True
        )
        middleware_process.register_callback(middleware_started_callback)
        middleware_process.start()
        finished = False
        while not finished:
            finished = middleware_process.get_parsed_data()

    except Exception as e:
        logger.error(
            f"An error occurred while starting {SERVICE_NAME}: {e}")
        # This is important, propogate this one
        raise
