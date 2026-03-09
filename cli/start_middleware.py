import logging
import cli.proccess as process
import os
import enum
import config.config as config
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


def build_middleware_argv(
    binary_path: str,
    release: bool,
    INTERFACE_TYPE: InterfaceType,
    DEVICE_PATH: str,
    PENDANT_SOCKET_PATH: str,
    WEB_CONTROL_SOCKET_PATH: str,
    opt_arg: Optional[str] = None,
    lora_config: Optional[dict] = None,
) -> List[str]:
    """Build the argv list for the middleware process. No filesystem or side effects.
    Order: binary_path, interface_type, device_path, pendant_socket, web_socket,
    [lora params if UART], [opt_arg if present].
    """
    if not isinstance(INTERFACE_TYPE, InterfaceType):
        raise ValueError(
            f"INTERFACE_TYPE must be a InterfaceType value, got: {INTERFACE_TYPE} as type {type(INTERFACE_TYPE)}")
    argv = [
        binary_path,
        INTERFACE_TYPE.value,
        DEVICE_PATH,
        PENDANT_SOCKET_PATH,
        WEB_CONTROL_SOCKET_PATH,
    ]
    if INTERFACE_TYPE == InterfaceType.UART_E5:
        if lora_config is None:
            raise ValueError("UART_E5 interface requires lora_config")
        argv.extend([
            lora_config["frequency"],
            lora_config["spread_factor"],
            lora_config["bandwidth"],
            lora_config["tx_preamble"],
            lora_config["rx_preamble"],
            lora_config["power"],
            lora_config["crc"],
            lora_config["iq"],
            lora_config["net"],
        ])
    if opt_arg is not None:
        argv.append(opt_arg)
    return argv


def start_middleware(logger: logging.Logger,
                     release: bool,
                     INTERFACE_TYPE: InterfaceType,
                     DEVICE_PATH: str,
                     PENDANT_SOCKET_PATH: str,
                     WEB_CONTROL_SOCKET_PATH: str,
                     opt_arg: Optional[str] = None,
                     lora_config: Optional[dict] = None,
                     ):

    SERVICE_NAME = "middleware_server"
    try:
        BINARY_NAME = "middleware_release" if release else "middleware_debug"
        MIDDLEWARE_BINARY_PATH = get_middleware_path(BINARY_NAME, release)
        # Should always be relative to cwd. Just use the (.):
        # ./middleware/something-build/middleware_server {args}
        # See args in main.cpp
        if MIDDLEWARE_BINARY_PATH is None:
            logger.debug(f"WORKING DIRECTORY: {os.getcwd()}")
            raise FileNotFoundError(
                f"Could not find {SERVICE_NAME} binary ({BINARY_NAME}) in build folders or root folder. Please run $ bash scripts/release.sh")

        middleware_command = build_middleware_argv(
            MIDDLEWARE_BINARY_PATH,
            release,
            INTERFACE_TYPE,
            DEVICE_PATH,
            PENDANT_SOCKET_PATH,
            WEB_CONTROL_SOCKET_PATH,
            opt_arg=opt_arg,
            lora_config=lora_config,
        )

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
