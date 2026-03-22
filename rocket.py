#!/usr/bin/env python3

from functools import cache

import click
import cli.rocket_logging as rocket_logging
import cli.proccess as process
import config.config as config
import logging
import subprocess
import sys
import time
import os
import signal
import enum
from typing import Dict, Optional, Callable
from cli.start_socat import start_fake_serial_device
from cli.start_emulator import start_fake_serial_device_emulator
from cli.start_middleware_build import start_middleware_build, CMakeBuildModes
from cli.start_middleware import (
    start_middleware,
    InterfaceType,
    get_interface_type,
    MiddlewareConfig,
)
from cli.start_event_viewer import start_event_viewer
from cli.start_pendant_emulator import start_pendant_emulator
from cli.start_frontend_api import start_frontend_api
from cli.start_simulation import start_simulator
from cli.start_frontend_webserver import start_frontend_webserver
from cli.start_replay_system import (
    start_replay_system,
    get_available_missions,
    SimulationType,
)
from cli.start_pendant_daemon import start_pendant_daemon
from cli.start_dummy_critAlert import start_dummy_alert



logger: logging.Logger = None
cleanup_reason: str = (
    "Program completed or undefined exit"  # Default clenaup message
)
running_services: bool = False  # To help close the cli automatically


class Command(enum.Enum):
    """Command enums to help start services"""

    RUN = enum.auto()
    DEV = enum.auto()
    SIMULATION = enum.auto()
    REPLAY = enum.auto()


class DecoratorSelector(enum.Enum):
    """Selection options to build a decorator"""

    ALL_DEV = enum.auto()  # Give me all the dev options
    SIM = enum.auto()  # Give me the options for simulation
    GSE_ONLY = enum.auto()  # Give me just the GSE only option
    REPLAY = enum.auto()


class ControllerTypes(enum.Enum):
    """Nomenclature: this is also called a pendant"""

    F710 = enum.auto()
    RPI_GPIO_DEVICE = enum.auto()
    HID_DEVICE = enum.auto()
    PYGAME_DEVICE = enum.auto()
    NOT_IMPLIMENTED = enum.auto()


def cli_decorator_factory(SELECTOR: DecoratorSelector):
    """Factory function to create decorators based on the selector"""

    def _set_level(ctx, param, value):
        if value:
            CLEAN_VALUE = value.upper().strip()
            rocket_logging.set_console_log_level(CLEAN_VALUE)
        return value

    _LOG_LEVEL_CHOICES = click.Choice(
        list(rocket_logging.LOG_MAPPING.keys()), case_sensitive=False
    )
    _INTERFACE_CHOICES = click.Choice(
        [e.value for e in InterfaceType], case_sensitive=False
    )
    _MISSION_CHOICES = click.Choice(
        get_available_missions(), case_sensitive=False
    )

    _REPLAY_MODES = click.Choice(
        ["mission", "simulation"], case_sensitive=False
    )

    _SIMULATION_CHOICES = click.Choice(
        [e.value for e in SimulationType], case_sensitive=False
    )

    OPTIONS_GSE_ONLY = [
        click.option(
            "--gse-only", is_flag=True, help="Run the system in GSE only mode"
        )
    ]

    OPTIONS_SIM = [
        click.option(
            "-l",
            "--log-level",
            is_flag=False,
            type=_LOG_LEVEL_CHOICES,
            help="Overide the config log level",
            callback=_set_level,
            expose_value=False,
        ),
        click.option("--docker", is_flag=True, help="Run in Docker"),
        click.option(
            "--nobuild",
            is_flag=True,
            help="Do not build binaries. Search for pre-built binaries",
        ),
        click.option("--logpkt", is_flag=True, help="Log packet data to csv"),
    ]

    OPTIONS_REPLAY = [
        click.option(
            "-l",
            "--log-level",
            is_flag=False,
            type=_LOG_LEVEL_CHOICES,
            help="Overide the config log level",
            callback=_set_level,
            expose_value=False,
        ),
        click.option("--docker", is_flag=True, help="Run in Docker"),
        click.option(
            "--nobuild",
            is_flag=True,
            help="Do not build binaries. Search for pre-built binaries",
        ),
        click.option("--logpkt", is_flag=True, help="Log packet data to csv"),
        click.option(
            "--mode", type=_REPLAY_MODES, help="Select the replay mode"
        ),
        click.option(
            "--mission",
            type=_MISSION_CHOICES,
            help="Select what mission to replay (required for mission mode)",
        ),
        click.option(
            "-s",
            "--simulation",
            type=_SIMULATION_CHOICES,
            help="Select simulation type (required for simulation mode)",
        ),
    ]

    OPTIONS_ALL_DEV = (
        OPTIONS_SIM
        + OPTIONS_GSE_ONLY
        + [
            click.option(
                "-i",
                "--interface",
                type=_INTERFACE_CHOICES,
                help="Hardware interface type (single link). Overrides config. Mutually exclusive with --interface-av/--interface-gse.",
            ),
            click.option(
                "--interface-av",
                type=_INTERFACE_CHOICES,
                help="AV link interface type (dual-link mode). Must be used together with --interface-gse.",
            ),
            click.option(
                "--interface-gse",
                type=_INTERFACE_CHOICES,
                help="GSE link interface type (dual-link mode). Must be used together with --interface-av.",
            ),
            click.option(
                "--nopendant",
                is_flag=True,
                help="Do not run the pendant emulator",
            ),
            click.option(
                "--frontend", is_flag=True, help="Run GSC front end server"
            ),
            click.option(
                "--experimental",
                is_flag=True,
                help="Simulate ALL values over all possible domains",
            ),
            click.option(
                "--corruption",
                is_flag=True,
                help="Simulate heavy bit corruption",
            ),
        ]
    )

    if SELECTOR == DecoratorSelector.ALL_DEV:
        OPTIONS = OPTIONS_ALL_DEV
    elif SELECTOR == DecoratorSelector.SIM:
        OPTIONS = OPTIONS_SIM
    elif SELECTOR == DecoratorSelector.GSE_ONLY:
        OPTIONS = OPTIONS_GSE_ONLY
    elif SELECTOR == DecoratorSelector.REPLAY:
        OPTIONS = OPTIONS_REPLAY

    def decorator(func: Callable) -> Callable:
        # Apply in reverse so the first in the list appears first in --help
        for option in reversed(OPTIONS):
            func = option(func)
        return func

    return decorator


def start_docker_container(logger):
    try:
        logger.info("Building dev container")
        subprocess.run(
            [
                "docker",
                "build",
                "-t",
                "rocket-dev",
                "-f",
                "docker/Dockerfile.dev",
                ".",
            ],
            check=True,
        )
        logger.info("Running dev container")
        subprocess.run(
            ["docker", "run", "--rm", "-it", "rocket-dev"], check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start Docker container: {e}")
        DOCKER_WARNING_TEXT = "PLEASE ENSURE DOCKER ENGINE IS RUNNING"
        logger.error(f"{'-'*len(DOCKER_WARNING_TEXT)}")
        logger.error(DOCKER_WARNING_TEXT)
        logger.error(f"{'-'*len(DOCKER_WARNING_TEXT)}")
        raise


def get_controller_enum() -> ControllerTypes:
    pedant_config = config.get_config()["hardware"].get("controller")
    if pedant_config is None or len(pedant_config) == 0:
        # Nothing specified
        raise RuntimeError("Pendant controller option not found in config.ini")
    match pedant_config.lower().strip():
        case "f710":
            return ControllerTypes.F710
        case "rpi_gpio_device":
            return ControllerTypes.RPI_GPIO_DEVICE
        case "hid_device":
            return ControllerTypes.HID_DEVICE
        case "pygame_device":
            return ControllerTypes.PYGAME_DEVICE
        case _:
            raise RuntimeError(
                "Pendant controller option not found in config.ini"
            )


# Used to tell the sleep deprived operator what the current configs are on bootup
# Explicit and obvious. Don't assume what frequency you are on


def large_radio_config_print(params):
    logger.info("----------# RADIO PARAMETERS #----------")
    for key, value in params.items():
        logger.info(f"{key}:\t {value}")
    logger.info("----------# RADIO PARAMETERS #----------")


def _validate_interface_options(
    interface: Optional[str],
    interface_av: Optional[str],
    interface_gse: Optional[str],
) -> None:
    """Validate mutual exclusivity of --interface vs --interface-av/--interface-gse.
    Raises click.UsageError for invalid combinations.
    """
    has_single = interface is not None
    has_av = interface_av is not None
    has_gse = interface_gse is not None
    if has_single and (has_av or has_gse):
        raise click.UsageError(
            "Do not specify both --interface and --interface-av/--interface-gse. "
            "Use either --interface (single link) or both --interface-av and --interface-gse (separate links)."
        )
    if (has_av and not has_gse) or (has_gse and not has_av):
        raise click.UsageError(
            "When using separate links, both --interface-av and --interface-gse must be specified."
        )

    if interface_av is not None:
        interface_av = interface_av.strip().lower()

    if interface_gse is not None:
        interface_gse = interface_gse.strip().lower()

    if interface_gse is not None and interface_av is not None:
        if (
            "test" in interface_av
            or "test" in interface_gse
            and interface_av != interface_gse
        ):
            raise NotImplementedError(
                "Device emulator does not support split emulation interfaces yet"
            )


def start_services(
    COMMAND: Command,
    DOCKER: bool = False,
    interface_av_arg: Optional[str] = None,
    interface_gse_arg: Optional[str] = None,
    nobuild: bool = False,
    logpkt: bool = False,
    nopendant: bool = False,
    gse_only: bool = False,
    frontend: bool = False,
    replay_mode: Optional[str] = None,
    MISSION_ARG: Optional[str] = None,
    SIMULATION_ARG: Optional[str] = None,
    experimental: bool = False,
    corruption: bool = False,
):
    """Starts all services required for the given command.

    Args:
        COMMAND (Command): Summoning command for context.
        DOCKER (bool, optional): Start in docker?. Defaults to False.
        interface_av_arg (Optional[str], optional): AV link type for dual-link mode. With interface_gse_arg. Defaults to None.
        interface_gse_arg (Optional[str], optional): GSE link type for dual-link mode. With interface_av_arg. Defaults to None.
        nobuild (bool, optional): Skip cmake build?. Defaults to False.
        logpkt (bool, optional): Log recieved packets?. Defaults to False.
        nopendant (bool, optional): Don't start GSE control pendant?. Defaults to False.
        gse_only (bool, optional): Only communicate with GSE?. Defaults to False.
        frontend (bool, optional): Start the frontend server?. Defaults to False.
        replay_mode (Optional[str], optional): _description_. Defaults to None.
        MISSION_ARG (Optional[str], optional): _description_. Defaults to None.
        SIMULATION_ARG (Optional[str], optional): _description_. Defaults to None.
        experimental (bool, optional): Simulate all possible values over the entire domain. Defaults to False.
        corruption (bool, optional): Corrupt data packets to simulate heavy bit corruption. Defaults to False.

    Raises:
        NotImplementedError: _description_
        ValueError: _description_
    """
    global running_services
    running_services = True

    print_splash()

    # 0 Notify user if they are in release mode
    if COMMAND == Command.RUN:
        logger.info("------- STARTING SOTERIA IN PRODUCTION MODE -------")
        logger.info("------- STARTING SOTERIA IN PRODUCTION MODE -------")
        logger.info("------- STARTING SOTERIA IN PRODUCTION MODE -------")

    # 0.1 Start docker container if requested in dev environment
    if not DOCKER:
        # This is called in Docker anyway.
        # Just to avoid recursive containerisation
        logger.info("Starting Soteria")
    else:
        logger.info("Starting Soteria container in Docker")
        raise NotImplementedError(
            "Internal Docker implimentation is out of date. Do not use"
        )
        start_docker_container(logger)

    # 1 Build C++ middleware
    if not nobuild:
        try:
            start_middleware_build(logger, CMakeBuildModes.DEBUG)
        except Exception as e:
            logger.error(
                f"Failed to build middleware: {e}\nPropogating fatal error"
            )
            raise
    else:
        logger.info("Skipping middleware build. Using pre-built binaries")

    # 2. Resolve GSE and AV interface types (single = same for both; dual = separate)
    dual_mode = interface_av_arg is not None and interface_gse_arg is not None

    INTERFACE_TYPE_GSE = get_interface_type(interface_gse_arg)
    INTERFACE_TYPE_AV = get_interface_type(interface_av_arg)

    if (
        os.environ.get("PYTEST_CURRENT_TEST") is not None
        and os.environ.get("CI_BUILD_ENV") == "Run"
    ):
        # You are in testing release environment
        raise NotImplementedError("Release python testing is not implemented")

    lora_config = {}
    match INTERFACE_TYPE_GSE:
        case InterfaceType.UART_E5:
            logger.info("Starting UART E5 interface (GSE)")
            devices = ("/dev/serial0", None)
            lora_section = config.get_config()["lora"]
            lora_config = {
                "frequency": str(lora_section.get("frequency")),
                "spread_factor": str(lora_section.get("spread_factor")),
                "bandwidth": str(lora_section.get("bandwidth")),
                "tx_preamble": str(lora_section.get("tx_preamble")),
                "rx_preamble": str(lora_section.get("rx_preamble")),
                "power": str(lora_section.get("power")),
                "crc": str(lora_section.get("crc")),
                "iq": str(lora_section.get("iq")),
                "net": str(lora_section.get("net")),
            }
            large_radio_config_print(lora_section)
        case InterfaceType.TEST_UART_E5:
            devices = run_pseudoterm_setup(COMMAND)
        case InterfaceType.TEST:
            devices = run_pseudoterm_setup(COMMAND)
        case InterfaceType.TCP:
            logger.info("Starting TCP interface")
            tcp_ip = str(config.get_config()["tcp"].get("gse_ip"))
            tcp_port = int(config.get_config()["tcp"].get("gse_port"))
            large_radio_config_print(config.get_config()["tcp"])
            if tcp_ip is None or tcp_port is None:
                raise RuntimeError(
                    "Please specify gse_ip and gse_port in config/config.ini"
                )
            if not (1 <= tcp_port <= 65535):
                raise RuntimeError("tcp-port must be between 1 and 65535")
            devices = (f"{tcp_ip}:{tcp_port}", None)
        case _:
            logger.error("Invalid interface type")
            raise ValueError("Invalid interface type")

    # 3. Run C++ middleware (always gse + av argv; single = same type/path for both)
    try:
        optional_arg = "--GSE_ONLY" if gse_only else None
        device_path = devices[0]
        # Adding shit to the middleware args is annoying as fuck
        # This needs to be refactored and SSOT / DRY fixed
        mw_config = MiddlewareConfig(
            release=COMMAND == Command.RUN,
            interface_gse_type=INTERFACE_TYPE_GSE,
            device_path_gse=device_path,
            interface_av_type=INTERFACE_TYPE_AV,
            device_path_av=device_path,
            pendant_socket_path="gcs_rocket",
            web_control_socket_path=os.path.abspath(
                os.path.join(os.path.sep, "tmp", "gcs_rocket_web_pull.sock")
            ),
            opt_arg=optional_arg,
            lora_config=(
                lora_config
                if INTERFACE_TYPE_GSE == InterfaceType.UART_E5
                else None
            ),
        )
        start_middleware(logger=logger, config=mw_config)
    except Exception as e:
        logger.error(
            f"Failed to start middleware: {e}\nPropogating fatal error"
        )
        raise

    # 4. Start device emulator
    # TODO maybe consider blocking further starts if this fails?
    # Would only be for convienece though. It isn't really required or critical
    if (
        INTERFACE_TYPE_AV in [InterfaceType.TEST, InterfaceType.TEST_UART_E5]
        or INTERFACE_TYPE_GSE
        in [InterfaceType.TEST, InterfaceType.TEST_UART_E5]
        and COMMAND == Command.DEV
    ):
        if INTERFACE_TYPE_AV != INTERFACE_TYPE_GSE:
            raise NotImplementedError(
                "Device emulator does not support split emulation interfaces yet"
            )
        start_fake_serial_device_emulator(
            logger,
            devices[1],
            INTERFACE_TYPE_AV,
            experimental=experimental,
            corruption=corruption,
        )
    elif COMMAND == Command.SIMULATION:
        start_simulator(logger, devices[1])
    elif COMMAND == Command.REPLAY:
        if replay_mode == "mission":
            start_replay_system(
                logger, devices[1], MISSION=MISSION_ARG, SIMULATION=None
            )
        else:
            start_replay_system(
                logger, devices[1], MISSION=None, SIMULATION=SIMULATION_ARG
            )

    # 5. Start the event viewer
    start_event_viewer(logger, "gcs_rocket", file_logging_enabled=logpkt)

    # 6. Start the pendent emulator
    if not nopendant:
        controller_enum = get_controller_enum()

        if controller_enum == ControllerTypes.F710:
            start_pendant_emulator(logger)
        elif controller_enum == ControllerTypes.NOT_IMPLIMENTED:
            raise NotImplementedError("Controller service not supported")
        else:
            start_pendant_daemon(logger)

    if frontend:
        # 7. Start the websocket / frontend API
        start_frontend_api(logger, "gcs_rocket")
        # 8. Start the frontend web server
        start_frontend_webserver(logger)

    # Appended On Dummy Service for Dummy Alert Logging
    start_dummy_alert(logger)


def run_pseudoterm_setup(COMMAND: Command):
    if COMMAND == Command.RUN:
        logger.warning("Test interface selected in production mode")
    logger.info("Starting pseudo-terminals for emulation")
    devices = start_fake_serial_device(logger)
    if devices == (None, None):
        raise RuntimeError("Failed to start fake serial device. Exiting")

    return devices


@click.group()
def cli():
    """CLI interface to manage GCS software initialisation"""
    # Check you're in a valid directory.
    # Implicit check is to make sure the logo file exists in expected spot
    if not os.path.exists(os.path.join("cli", "ascii_art_logo.txt")):
        raise RuntimeError(
            "Please run this program from project root directory"
        )


@click.command()
@cli_decorator_factory(DecoratorSelector.GSE_ONLY)
def run(gse_only):
    """Start software for launch day usage"""
    rocket_logging.set_console_log_level("INFO")
    interface_gse_arg = config.get_config()["hardware"].get(
        "interface_release_gse"
    )
    interface_av_arg = config.get_config()["hardware"].get(
        "interface_release_av"
    )
    start_services(
        Command.RUN,
        DOCKER=False,
        interface_av_arg=interface_av_arg,  # Use config only
        interface_gse_arg=interface_gse_arg,  # Use config only
        nobuild=True,  # Do NOT auto build in production mode.
        logpkt=True,  # Log packets by default in production mode
        nopendant=False,  # Pendant emulator is required in production mode
        gse_only=gse_only,
        frontend=True,  # Run frontend web server in production mode
    )


@click.command()
@cli_decorator_factory(DecoratorSelector.ALL_DEV)
def dev(
    docker,
    interface,
    interface_av,
    interface_gse,
    nobuild,
    logpkt,
    nopendant,
    gse_only,
    frontend,
    experimental,
    corruption,
):
    """Start software in development mode"""
    _validate_interface_options(interface, interface_av, interface_gse)
    if interface is not None:
        interface_av = interface
        interface_gse = interface
    start_services(
        Command.DEV,
        DOCKER=docker,
        interface_av_arg=interface_av,
        interface_gse_arg=interface_gse,
        nobuild=nobuild,
        logpkt=logpkt,
        nopendant=nopendant,
        gse_only=gse_only,
        frontend=frontend,
        experimental=experimental,
        corruption=corruption,
    )


@click.command()
@cli_decorator_factory(DecoratorSelector.SIM)
def simulation(docker, nobuild, logpkt):
    """Start software in simulation mode"""
    start_services(
        Command.SIMULATION,
        DOCKER=docker,
        INTERFACE_ARG="TEST",
        nobuild=nobuild,
        logpkt=logpkt,
        nopendant=True,
        gse_only=False,
        frontend=True,
    )


@click.command()
@cli_decorator_factory(DecoratorSelector.REPLAY)
def replay(docker, nobuild, logpkt, mode, mission, simulation):
    """Start software in simulation mode"""
    if not mode:
        raise click.UsageError("--mode is required for the replay engine")

    if mode == "mission":
        if not mission:
            raise click.UsageError(
                "--mission is required to run a specified mission"
            )
        elif mission == "TEST":
            raise NotImplementedError(f"{mission} has not been implemented yet")

        logger.info(f"Using mission data:{mission}")

    elif mode == "simulation":
        if not simulation:
            raise click.UsageError(
                "--simulation is required to run a specified scenario"
            )
        elif simulation != "TEST" and simulation != "DEMO":
            raise NotImplementedError(
                f"{simulation} has not been implemented yet"
            )
        logger.info(f"Running simulation: {simulation}")
    start_services(
        Command.REPLAY,
        DOCKER=docker,
        INTERFACE_ARG="TEST",
        nobuild=nobuild,
        logpkt=logpkt,
        nopendant=True,
        gse_only=False,
        frontend=True,
        replay_mode=mode,
        MISSION_ARG=mission,
        SIMULATION_ARG=simulation,
    )


def print_splash():
    """Prints a logo and splash screen for decoration"""
    with open(os.path.join("cli", "ascii_art_logo.txt"), "r") as r:
        print(r.read())

    print("\n\n")
    print("RMIT High Velocty Rocket GCS CLI")
    print("Version: ", end="")
    with open("VERSION", "r") as r:
        print(r.read())

    print(
        "Local Timestamp: ",
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
    )

    print("\n")


def signal_handler(signum, frame):
    """Handle system signals and set an appropriate cleanup reason"""
    global cleanup_reason
    signal_map = {
        signal.SIGINT: "Keyboard Interrupt (SIGINT)",
        signal.SIGTERM: "Termination Request (SIGTERM)",
        signal.SIGHUP: "Terminal Hangup (SIGHUP)",
        signal.SIGQUIT: "Quit Signal (SIGQUIT)",
    }
    if signum in signal_map:
        cleanup_reason = signal_map[signum]
    else:
        cleanup_reason = f"Recieved unhandled signal: {signum}"
    cleanup()
    # This can be a graceful exit for now.
    # Might need to change for CI tests in future
    sys.exit(0)


def cleanup():
    """Run cleanup tasks before the program exits"""
    if "Keyboard Interrupt" in cleanup_reason:
        print()  # Print a newline after the ^C
    logger.warning(f"Running cleanup tasks - Reason: {cleanup_reason}")
    process.LoggedSubProcess.cleanup()
    logger.info("All cleanup tasks completed")


def main():
    global logger, cleanup_reason

    # Use groups for nested positional arugments `rocket run dev/prod`
    cli.add_command(run)
    cli.add_command(dev)
    cli.add_command(simulation)
    cli.add_command(replay)

    # Register custom signal handlers
    signal.signal(signal.SIGINT, signal_handler)  # Handle Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Handle process termination
    signal.signal(signal.SIGHUP, signal_handler)  # Handle terminal close
    # Handle quit signal (Ctrl+\)
    signal.signal(signal.SIGQUIT, signal_handler)

    # Remove stale tmp files
    GCS_CONFIG_HELPER_PATH = os.path.join(
        os.path.sep, "tmp", "GCS_CONFIG_LOCATION.txt"
    )
    if os.path.exists(GCS_CONFIG_HELPER_PATH):
        os.remove(GCS_CONFIG_HELPER_PATH)

    rocket_logging.initialise()
    logger = logging.getLogger("rocket")

    try:
        # Tell click CLI to let me handle exceptions and stuff.
        # This is because we're in charge of subprocess and threads
        cli.main(args=sys.argv[1:], standalone_mode=False)

        # After CLI setup is done, start waiting (not busy waiting please)
        if running_services:
            while True:
                # Keep program alive, but it doesn't need to do anything
                time.sleep(1)

    except Exception as e:
        cleanup_reason = f"Unhandled Exception: {e}"
        cleanup()
        # I hope this doesn't mess with CI test results
        raise  # Re-raise the exception after cleanup


if __name__ == "__main__":
    main()
