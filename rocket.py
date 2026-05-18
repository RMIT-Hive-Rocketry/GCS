#!/usr/bin/env python3

import click
import cli.rocket_logging as rocket_logging
import cli.process as process
import config.config as config
import logging
import subprocess
import sys
import time
import os
import signal
import enum
from collections.abc import Callable
from cli.start_emulator import start_fake_serial_device_emulator
from cli.start_middleware_build import start_middleware_build, CMakeBuildModes
from cli.start_middleware import start_middleware, InterfaceType
from cli.start_event_viewer import start_event_viewer
from cli.start_pendant_emulator import start_pendant_emulator
from cli.start_frontend_api import start_frontend_api
from cli.start_simulation import start_simulator
from cli.start_frontend_webserver import start_frontend_webserver
from cli.start_performance_monitor import start_performance_monitor
from cli.start_replay_system import (
    start_replay_system,
    get_available_missions,
    get_available_blue_ravens,
    SimulationType,
)
from cli.start_pendant_daemon import start_pendant_daemon
from cli.runtime_launch_config import RuntimeLaunchConfig


logger: logging.Logger = None
cleanup_reason: str = (
    "Program completed or undefined exit"  # Default clenaup message
)
RUNNING_SERVICES: bool = False  # To help close the cli automatically

IN_TEST_ENVIRONMENT: bool = os.environ.get("PYTEST_CURRENT_TEST", False)

RunningProcesses = process.RunningProcess()

APP_START_TIME = None  # Start Time Of application initialized within main before logging starts


class Command(enum.Enum):
    """Command enums to help start services"""

    RUN = enum.auto()
    DEV = enum.auto()
    SIMULATION = enum.auto()
    REPLAY = enum.auto()


class DecoratorSelector(enum.Enum):
    """Selection options to build a decorator"""

    ALL_RUN = enum.auto()  # Give me just the GSE only and frontend only options
    ALL_DEV = enum.auto()  # Give me all the dev options
    SIM = enum.auto()  # Give me the options for simulation
    REPLAY = enum.auto()


def cli_decorator_factory(selector: DecoratorSelector) -> Callable:
    """Factory function to create decorators based on the selector"""

    def _set_level(ctx, param, value) -> str:
        if value:
            clean_value = value.upper().strip()
            rocket_logging.set_console_log_level(clean_value)
        return value

    _log_level_choices = click.Choice(
        list(rocket_logging.LOG_MAPPING.keys()), case_sensitive=False
    )
    _interface_choices = click.Choice(
        [e.value for e in InterfaceType], case_sensitive=False
    )
    _mission_choices = click.Choice(
        get_available_missions(), case_sensitive=False
    )
    _blue_raven_choices = click.Choice(
        get_available_blue_ravens(), case_sensitive=False
    )
    _replay_modes = click.Choice(
        ["mission", "simulation"], case_sensitive=False
    )
    _simulation_choices = click.Choice(
        [e.value for e in SimulationType], case_sensitive=False
    )

    options_gse_only = [
        click.option(
            "--gse-only", is_flag=True, help="Run the system in GSE only mode"
        )
    ]

    options_frontend_only = [
        click.option(
            "--frontend-only",
            is_flag=True,
            help="Run the system in frontend only mode",
        ),
    ]

    options_sim = [
        click.option(
            "-l",
            "--log-level",
            is_flag=False,
            type=_log_level_choices,
            help="Override the config log level",
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

    options_replay = [
        click.option(
            "-l",
            "--log-level",
            is_flag=False,
            type=_log_level_choices,
            help="Override the config log level",
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
            "--mode", type=_replay_modes, help="Select the replay mode"
        ),
        click.option(
            "--mission",
            type=_mission_choices,
            help="Select what mission to replay (required for mission mode)",
        ),
        click.option(
            "--blue-raven",
            type=_blue_raven_choices,
            help="Select what mission to replay (required for mission mode)",
        ),
        click.option(
            "-s",
            "--simulation",
            type=_simulation_choices,
            help="Select simulation type (required for simulation mode)",
        ),
    ]

    options_all_run = options_gse_only + options_frontend_only

    options_all_dev = (
        options_sim
        + options_gse_only
        + options_frontend_only
        + [
            click.option(
                "-i",
                "--interface",
                type=_interface_choices,
                help="Hardware interface type (single link). Overrides config. Mutually exclusive with --interface-av/--interface-gse.",
            ),
            click.option(
                "--interface-av",
                type=_interface_choices,
                help="AV link interface type (dual-link mode). Must be used together with --interface-gse.",
            ),
            click.option(
                "--interface-gse",
                type=_interface_choices,
                help="GSE link interface type (dual-link mode). Must be used together with --interface-av.",
            ),
            click.option(
                "--nopendant",
                is_flag=True,
                help="Do not run the pendant emulator",
            ),
            click.option(
                "-f", "--frontend", is_flag=True, help="Run frontend web server"
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

    if selector == DecoratorSelector.ALL_RUN:
        options = options_all_run
    elif selector == DecoratorSelector.ALL_DEV:
        options = options_all_dev
    elif selector == DecoratorSelector.SIM:
        options = options_sim
    elif selector == DecoratorSelector.REPLAY:
        options = options_replay

    def decorator(func: Callable) -> Callable:
        # Apply in reverse so the first in the list appears first in --help
        for option in reversed(options):
            func = option(func)
        return func

    return decorator


def start_docker_container(logger) -> None:
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
        docker_warning_text = "PLEASE ENSURE docker ENGINE IS RUNNING"
        logger.error(f"Failed to start Docker container: {e}")
        logger.error(f"{'-'*len(docker_warning_text)}")
        logger.error(docker_warning_text)
        logger.error(f"{'-'*len(docker_warning_text)}")
        raise


def _validate_interface_options(
    interface: str | None,
    interface_av: str | None,
    interface_gse: str | None,
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

    if (
        interface_gse is not None
        and interface_av is not None
        and (
            "test" in interface_av
            or "test" in interface_gse
            and interface_av != interface_gse
        )
    ):
        raise NotImplementedError(
            "Device emulator does not support split emulation interfaces yet"
        )


def _validate_mutually_exclusive_options(
    gse_only: bool, frontend_only: bool
) -> None:
    """
    Validate mutual exclusivity of --gse-only and --frontend-only.
    Raises click.UsageError for invalid combinations.
    """
    if gse_only and frontend_only:
        raise click.UsageError(
            "Do not specify both --gse-only and --frontend-only"
        )


def start_services(
    command: Command,
    docker: bool = False,
    interface_av_arg: str | None = None,
    interface_gse_arg: str | None = None,
    nobuild: bool = False,
    logpkt: bool = False,
    nopendant: bool = False,
    gse_only: bool = False,
    frontend: bool = False,
    frontend_only: bool = False,
    replay_mode: str | None = None,
    mission_arg: str | None = None,
    blue_raven_arg: str | None = None,
    simulation_arg: str | None = None,
    experimental: bool = False,
    corruption: bool = False,
) -> None:
    """Starts all services required for the given command.

    Args:
        command (Command): Summoning command for context.
        docker (bool, optional): Start in docker?. Defaults to False.
        interface_av_arg (str, optional): AV link type for dual-link mode. With interface_gse_arg. Defaults to None.
        interface_gse_arg (str, optional): GSE link type for dual-link mode. With interface_av_arg. Defaults to None.
        nobuild (bool, optional): Skip cmake build?. Defaults to False.
        logpkt (bool, optional): Log received packets?. Defaults to False.
        nopendant (bool, optional): Don't start GSE control pendant?. Defaults to False.
        gse_only (bool, optional): Only communicate with GSE?. Defaults to False.
        frontend (bool, optional): Start the frontend server?. Defaults to False.
        frontend_only (bool, optional): Only start the frontend server. Defaults to None.
        replay_mode (str, optional): _description_. Defaults to None.
        mission_arg (str, optional): _description_. Defaults to None.
        simulation_arg (str, optional): _description_. Defaults to None.
        experimental (bool, optional): Simulate all possible values over the entire domain. Defaults to False.
        corruption (bool, optional): Corrupt data packets to simulate heavy bit corruption. Defaults to False.

    Raises:
        NotImplementedError: _description_
        ValueError: _description_
    """
    global RUNNING_SERVICES, APP_START_TIME
    RUNNING_SERVICES = True

    print_splash()

    # 0 Notify user if they are in release mode
    if command == Command.RUN:
        logger.info("------- STARTING SOTERIA IN PRODUCTION MODE -------")
        logger.info("------- STARTING SOTERIA IN PRODUCTION MODE -------")
        logger.info("------- STARTING SOTERIA IN PRODUCTION MODE -------")

    # 0.1 Start docker container if requested in dev environment
    if not docker:
        # This is called in Docker anyway.
        # Just to avoid recursive containerisation
        logger.info("Starting Soteria")
    else:
        logger.info("Starting Soteria container in Docker")
        raise NotImplementedError(
            "Internal Docker implementation is out of date. Do not use"
        )
        start_docker_container(logger)

    # 0.2 Interrupt further process loading if --frontend-only is being used
    if frontend_only is not None and frontend_only == True:
        start_frontend_webserver(logger)
        return

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

    if IN_TEST_ENVIRONMENT and os.environ.get("CI_BUILD_ENV") == "Run":
        # You are in testing release environment
        raise NotImplementedError("Release python testing is not implemented")

    launch_config = RuntimeLaunchConfig(
        command=command,
        interface_av_arg=interface_av_arg,
        interface_gse_arg=interface_gse_arg,
        gse_only=gse_only,
        logger=logger,
    )

    # 3. Run C++ middleware (always gse + av argv; single = same type/path for both)
    try:
        start_middleware(
            logger=logger,
            performance_logging=RunningProcesses,
            config=launch_config.middleware_config,
        )
    except Exception as e:
        logger.error(
            f"Failed to start middleware: {e}\nPropogating fatal error"
        )
        raise

    # 4. Start device emulator
    # TODO maybe consider blocking further starts if this fails?
    # Would only be for convienece though. It isn't really required or critical
    aux_service_plan = launch_config.build_aux_service_plan(
        replay_mode=replay_mode,
        mission_arg=mission_arg,
        simulation_arg=simulation_arg,
        blue_raven_arg=blue_raven_arg
    )
    if aux_service_plan.service == "emulator":
        start_fake_serial_device_emulator(
            logger,
            RunningProcesses,
            aux_service_plan.device_path,
            aux_service_plan.interface_type,
            experimental=experimental,
            corruption=corruption,
        )
    elif aux_service_plan.service == "simulator":
        start_simulator(logger, aux_service_plan.device_path)
    elif aux_service_plan.service == "replay":
        start_replay_system(
            logger,
            aux_service_plan.device_path,
            mission=aux_service_plan.mission,
            blue_raven=aux_service_plan.blue_raven,
            simulation=aux_service_plan.simulation
        )

    # 5. Start the event viewer
    start_event_viewer(
        logger=logger,
        performance_logging=RunningProcesses,
        socket_path="gcs_rocket",
        file_logging_enabled=logpkt,
    )

    # 5. Start the pendent emulator
    if not nopendant:
        launch_pendant_daemon = (
            config.get_config()["hardware"]["send_pendant_state_to_server"]
            == "true"
        )
        if launch_pendant_daemon:
            start_pendant_daemon(logger, RunningProcesses)
        else:
            start_pendant_emulator(logger, RunningProcesses)

    # 6. Start the websocket / frontend API
    # This should be able to run even without the frontend enabled, so it can be run on other devices
    start_frontend_api(logger, RunningProcesses, "gcs_rocket")

    # 7. Start the frontend web server
    if frontend:
        start_frontend_webserver(logger, RunningProcesses)

    # 8. Start performance monitor after all other services have started
    start_performance_monitor(
        logger=logger,
        performance_logging=RunningProcesses,
        start_time=APP_START_TIME,
    )


@click.group()
def cli() -> None:
    """CLI interface to manage GCS software initialisation"""
    # Check you're in a valid directory.
    # Implicit check is to make sure the logo file exists in expected spot
    if not os.path.exists(os.path.join("cli", "ascii_art_logo.txt")):
        raise RuntimeError(
            "Please run this program from project root directory"
        )


@click.command()
@cli_decorator_factory(DecoratorSelector.ALL_RUN)
def run(gse_only, frontend_only) -> None:
    """Start software for launch day usage"""
    rocket_logging.set_console_log_level("INFO")
    rocket_logging.set_console_low_detail(True)
    _validate_mutually_exclusive_options(gse_only, frontend_only)

    interface_gse_arg = config.get_config()["hardware"].get(
        "interface_release_gse"
    )
    interface_av_arg = config.get_config()["hardware"].get(
        "interface_release_av"
    )

    start_services(
        Command.RUN,
        docker=False,
        interface_av_arg=interface_av_arg,  # Use config only
        interface_gse_arg=interface_gse_arg,  # Use config only
        nobuild=True,  # Do NOT auto build in production mode.
        logpkt=True,  # Log packets by default in production mode
        nopendant=False,  # Pendant emulator is required in production mode
        gse_only=gse_only,
        frontend=True,  # Run frontend web server in production mode
        frontend_only=frontend_only,
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
    frontend_only,
    experimental,
    corruption,
) -> None:
    """Start software in development mode"""
    _validate_interface_options(interface, interface_av, interface_gse)
    _validate_mutually_exclusive_options(gse_only, frontend_only)
    if interface is not None:
        interface_av = interface
        interface_gse = interface
    start_services(
        Command.DEV,
        docker=docker,
        interface_av_arg=interface_av,
        interface_gse_arg=interface_gse,
        nobuild=nobuild,
        logpkt=logpkt,
        nopendant=nopendant,
        gse_only=gse_only,
        frontend=frontend,
        frontend_only=frontend_only,
        experimental=experimental,
        corruption=corruption,
    )


@click.command()
@cli_decorator_factory(DecoratorSelector.SIM)
def simulation(docker, nobuild, logpkt) -> None:
    """Start software in simulation mode"""
    start_services(
        Command.SIMULATION,
        docker=docker,
        interface_av_arg="TEST",
        interface_gse_arg="TEST",
        nobuild=nobuild,
        logpkt=logpkt,
        nopendant=True,
        gse_only=False,
        frontend=True,
        frontend_only=False,
    )


@click.command()
@cli_decorator_factory(DecoratorSelector.REPLAY)
def replay(docker, nobuild, logpkt, mode, mission, blue_raven, simulation) -> None:
    """Start software in simulation mode"""
    if not mode:
        raise click.UsageError("--mode is required for the replay engine")

    if mode == "mission":
        if not mission and not blue_raven:
            raise click.UsageError(
                "--mission or --blue-raven is required to run a specified mission"
            )
        if mission == "TEST":
            raise NotImplementedError(f"{mission} has not been implemented yet")

        logger.info(f"Using mission data:{mission}")

    elif mode == "simulation":
        if not simulation:
            raise click.UsageError(
                "--simulation is required to run a specified scenario"
            )
        if simulation != "TEST" and simulation != "DEMO":
            raise NotImplementedError(
                f"{simulation} has not been implemented yet"
            )
        logger.info(f"Running simulation: {simulation}")
    start_services(
        Command.REPLAY,
        docker=docker,
        interface_av_arg="TEST",
        interface_gse_arg="TEST",
        nobuild=nobuild,
        logpkt=logpkt,
        nopendant=True,
        gse_only=False,
        frontend=True,
        frontend_only=False,
        replay_mode=mode,
        mission_arg=mission,
        blue_raven_arg=blue_raven,
        simulation_arg=simulation,
    )


def print_splash() -> None:
    """Prints a logo and splash screen for decoration"""
    with open(os.path.join("cli", "ascii_art_logo.txt")) as r:
        print(r.read())

    print("\n\n")
    print("RMIT High Velocty Rocket GCS CLI")
    print("Version: ", end="")
    with open("VERSION") as r:
        print(r.read())

    print(
        "Local Timestamp: ",
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
    )

    print("\n")


def signal_handler(signum, frame) -> None:
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
        cleanup_reason = f"Received unhandled signal: {signum}"
    cleanup()
    # This can be a graceful exit for now.
    # Might need to change for CI tests in future
    sys.exit(0)


def cleanup() -> None:
    """Run cleanup tasks before the program exits"""
    if "Keyboard Interrupt" in cleanup_reason:
        print()  # Print a newline after the ^C
    logger.warning(f"Running cleanup tasks - Reason: {cleanup_reason}")
    process.LoggedSubProcess.cleanup()
    logger.info("All cleanup tasks completed")


def main() -> None:
    global logger, cleanup_reason

    # Use groups for nested positional arguments `rocket run dev/prod`
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
    gcs_config_helper_path = os.path.join(
        os.path.sep, "tmp", "GCS_CONFIG_LOCATION.txt"
    )
    if os.path.exists(gcs_config_helper_path):
        os.remove(gcs_config_helper_path)

    global APP_START_TIME
    APP_START_TIME = time.perf_counter()
    rocket_logging.initialise(APP_START_TIME)
    logger = logging.getLogger("rocket")
    if IN_TEST_ENVIRONMENT:
        rocket_logging.set_console_low_detail(False)

    try:
        # Tell click CLI to let me handle exceptions and stuff.
        # This is because we're in charge of subprocess and threads
        cli.main(args=sys.argv[1:], standalone_mode=False)

        # After CLI setup is done, start waiting (not busy waiting please)
        if RUNNING_SERVICES:
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
