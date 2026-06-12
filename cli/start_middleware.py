import logging
from cli import process
import os
from enum import StrEnum
from dataclasses import dataclass


class InterfaceType(StrEnum):
    # Reference the main middleware cpp file
    UART_E5 = "UART_E5"
    UART_FEATHER = "UART_FEATHER"
    TEST = "TEST"
    TEST_UART_E5 = "TEST_UART_E5"
    TCP = "TCP"

    # for --gse-only
    # acts like a release interface, but can be used in split emulation
    NONE = "NONE"


def get_interface_type(interface: str) -> InterfaceType:
    """Get the interface type from the command line argument"""
    interface = interface.strip().upper()

    # Convert string to InterfaceType enum
    try:
        try:
            return InterfaceType(interface)
        except ValueError as e:
            # If we get here, no matching enum value was found
            valid_types = [e.name for e in InterfaceType]

            # propagate error
            raise ValueError(
                f"Invalid interface type: '{interface}'. Valid types are: {', '.join(valid_types)}"
            ) from e
    except Exception as e:
        raise ValueError(f"Invalid interface type: {interface}") from e


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
    # I am confused as to why this is called pendant_socket_path?
    # - from idiot who wrote this code
    pendant_socket_path: str = "gcs_rocket"
    web_control_socket_path: str | None = None
    opt_arg: str | None = None
    lora_config: dict | None = None


class MiddlewareSubprocess(process.LoggedSubProcess):
    """Subclass of LoggedSubProcess with a stop condition for callbacks."""

    def _update_callback_condition(self) -> bool:
        if self._callback_hits >= 1:
            self._logger_adapter.debug(
                "Stopping build callbacks for this process"
            )
            return True
        return False


def middleware_started_callback(line: str, stream_name: str) -> bool | None:
    """Check if middleware has started"""

    if "Middleware server started successfully" in line:
        return True
    return None


def get_middleware_path(binary_name_prefix: str, release: bool) -> str | None:
    """Check if middleware is in build/ then check if it is in root folder.
    This helps when sharing releases, but still prioritises the build/ folder.
    """

    build_dir = "build-release" if release else "build-debug"

    # Cmake folder
    build_path_abs = os.path.join(os.getcwd(), build_dir)
    if not os.path.exists(build_path_abs):
        os.makedirs(build_path_abs)
    build_path_files = [
        os.path.join(build_path_abs, x) for x in os.listdir(build_path_abs)
    ]
    build_path_files = [x for x in build_path_files if os.path.isfile(x)]

    # User placed
    project_path_abs = os.getcwd()
    project_root_files = [
        os.path.join(project_path_abs, x) for x in os.listdir(project_path_abs)
    ]
    project_root_files = [x for x in project_root_files if os.path.isfile(x)]

    file_matches = []
    for path in build_path_files + project_root_files:
        filename = os.path.basename(path)
        if filename.startswith(binary_name_prefix):
            file_matches.append(path)

    if len(file_matches) > 1:
        raise RuntimeError(
            f"Multiple middleware binaries found. Please remove or archive the extra ones: {file_matches}"
        )
    if len(file_matches) == 0:
        return None

    binary_path = file_matches[0]

    with open("VERSION") as f:
        version_string = f.read().strip()

    # Actual file may have build metadata in it. Substring match is fine
    if version_string not in os.path.basename(binary_path):
        raise RuntimeError(
            f"Middleware binary version mismatch. Expected prefix: {version_string}, found: {os.path.basename(binary_path)}. The repository branch VERSION file does not match the binary version found"
        )

    return file_matches[0]


def build_middleware_argv(
    config: MiddlewareConfig, binary_path: str
) -> list[str]:
    """Build argv for the middleware process (always gse + av format).

    Order: binary, gse_type, gse_path, av_type, av_path, pendant, web,
    [9 lora params if gse_type==UART_E5 or av_type==UART_E5], [--GSE-ONLY].
    """
    if not isinstance(
        config.interface_gse_type, InterfaceType
    ) or not isinstance(config.interface_av_type, InterfaceType):
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

    an_interface_is_uart_e5 = (
        config.interface_gse_type == InterfaceType.UART_E5
        or config.interface_av_type == InterfaceType.UART_E5
    )

    an_interface_is_uart_feather = InterfaceType.UART_FEATHER in (
        config.interface_gse_type,
        config.interface_av_type,
    )

    if an_interface_is_uart_e5:
        if config.lora_config is None:
            raise ValueError("UART_E5 interface requires lora_config")
        argv.extend(
            [
                config.lora_config["frequency"],
                config.lora_config["spread_factor"],
                config.lora_config["bandwidth"],
                config.lora_config["tx_preamble"],
                config.lora_config["rx_preamble"],
                config.lora_config["power"],
                config.lora_config["crc"],
                config.lora_config["iq"],
                config.lora_config["net"],
            ]
        )
    elif an_interface_is_uart_feather:
        # The Feather firmware only exposes frequency and power; modem
        # settings are fixed (125 kHz BW, CR 4/5, SF7)
        if config.lora_config is None:
            raise ValueError("UART_FEATHER interface requires lora_config")
        argv.extend(
            [
                config.lora_config["frequency"],
                config.lora_config["power"],
            ]
        )
    if config.opt_arg is not None:
        argv.append(config.opt_arg)
    return argv


def start_middleware(
    logger: logging.Logger,
    config: MiddlewareConfig,
    performance_logging: process.RunningProcess = None,
) -> None:

    service_name = "server"  # Formally the middleware_server
    if config.web_control_socket_path is None:
        config.web_control_socket_path = os.path.abspath(
            os.path.join(os.path.sep, "tmp", "gcs_rocket_web_pull.sock")
        )
    try:
        binary_name = (
            "middleware_release" if config.release else "middleware_debug"
        )
        middleware_binary_path = get_middleware_path(
            binary_name, config.release
        )
        if middleware_binary_path is None:
            logger.debug(f"WORKING DIRECTORY: {os.getcwd()}")
            raise FileNotFoundError(
                f"Could not find {service_name} binary ({binary_name}) in build folders or root folder. Please run $ bash scripts/release.sh"
            )

        middleware_command = build_middleware_argv(
            config, middleware_binary_path
        )

        logger.debug(f"Starting {service_name} with: {middleware_command}")

        middleware_process = MiddlewareSubprocess(
            middleware_command, name=service_name, parse_output=True
        )
        middleware_process.register_callback(middleware_started_callback)
        middleware_process.start()
        if performance_logging is not None:
            performance_logging.AddNewProcess(middleware_process)

        finished = False
        while not finished:
            finished = middleware_process.get_parsed_data()

    except Exception as e:
        logger.error(f"An error occurred while starting {service_name}: {e}")
        # This is important, propagate this one
        raise
