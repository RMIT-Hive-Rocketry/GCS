import logging
import cli.process as process
import enum
import os
import sys


class SimulationType(enum.Enum):
    TEST = "TEST"
    DEMO = "DEMO"
    LEGACY = "legacy"
    FAIL = "fail"


def get_available_missions() -> list[str]:
    """Scans the mission directory and then returns the available missions"""
    mission_path = os.path.join("backend", "replay_system", "mission_data")
    if not os.path.exists(mission_path):
        return []

    return [
        d
        for d in os.listdir(mission_path)
        if os.path.isdir(os.path.join(mission_path, d))
    ]

def get_available_blue_ravens() -> list[str]:
    """Scans the blue_raven directory and then returns the available missions"""
    blue_raven_path = os.path.join("backend", "replay_system", "blue_raven")
    if not os.path.exists(blue_raven_path):
        return []

    return [
        d
        for d in os.listdir(blue_raven_path)
        if os.path.exists(os.path.join(blue_raven_path, d))
    ]


def get_mission_path(mission: str | None) -> str:
    """Get the mission path from the command line argument, validation should exist already"""
    mission_path = os.path.join("backend", "replay_system", "mission_data")

    if mission is None:
        raise ValueError("Mission argument is required")

    full_mission_path = os.path.join(mission_path, mission)
    valid_missions = get_available_missions()
    if full_mission_path not in valid_missions:
        raise ValueError(
            f"Invalid Mission: {mission}. Valid missions are {', '. join(valid_missions)}"
        )
    return mission


def start_replay_system(
    logger: logging.Logger,
    device: str,
    mission: str | None = None,
    blue_raven: str | None = None,
    simulation: str | None = None,
) -> tuple[None, None] | None:
    """Starts the replay system either in simulation mode or mission mode

    Args:
        logger: Logger
        device: device
        mission: Mission directory name
        blue-raven: Mission blue raven file
        simulation: Simulation type
    """
    service_name = "replay system"
    try:
        args = 0
        if mission:
            args += 1
        if blue_raven:
            args += 1
        if simulation:
            args += 1
        
        if args == 0:
            raise ValueError("Must have either mission or blue-raven or simulation type")
        if args > 1:
            raise ValueError("Can only have one of simulation, mission or blue-raven data")
        
        replay_command = [
            sys.executable,
            "-u",
            os.path.join("backend", "replay_system", "replay_engine.py"),
            "--device-rocket",
            device,
        ]

        if mission:
            replay_command.extend(["--mode", "mission", "--mission", mission])
        elif blue_raven:
            replay_command.extend(["--mode", "mission", "--blue-raven", blue_raven])
        elif simulation:
            replay_command.extend(
                ["--mode", "simulation", "--simulation", simulation]
            )

        logger.debug(f"Starting {service_name} module with: {replay_command}")

        # Set up the PYTHONPATH to the project root to ensure the imports will work
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        emulator_process = process.LoggedSubProcess(
            replay_command,
            name=service_name,
            parse_output=True,
            env=env,
        )
        emulator_process.start()

    except Exception as e:
        logger.error(f"An error occurred while starting {service_name}: {e}")
        return None, None
