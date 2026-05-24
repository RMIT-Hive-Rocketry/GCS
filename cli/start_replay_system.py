import logging
from cli import process
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
    simulation: str | None = None,
) -> tuple[None, None] | None:
    """Starts the replay system either in simulation mode or mission mode

    Args:
        logger: Logger
        device: device
        mission: Mission directory name
        simulation: Simulation type
    """
    service_name = "replay system"
    try:
        if mission and simulation:
            raise ValueError("Can't have both simulation and mission data")

        if not mission and not simulation:
            raise ValueError("Must have either mission or simulation type")
        replay_command = [
            sys.executable,
            "-u",
            os.path.join("backend", "replay_system", "replay_engine.py"),
            "--device-rocket",
            device,
        ]
        if mission:
            replay_command.extend(["--mode", "mission", "--mission", mission])
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
