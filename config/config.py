from configparser import ConfigParser
from functools import cache
from typing import Dict
import os

# TODO
# Add field validation to every single config option.
# When get_config() loads it in, check that all fields are there and valid.
# If the field is critical, throw a runtime error. If not, display a slogger warning
# From fred, who is happy to chat with the next eager developer who finds this


def get_default_config_path():
    """
    Get absolute path based on where you're running the script.
    This is just stupid hard code because the hardware pendant is in a separate environment/process.
    Can remove this crap when you don't need pendant emulator anymore.
    """
    CONFIG_LOCATOR_FILE = os.path.join(
        os.path.sep, "tmp", "GCS_CONFIG_LOCATION.txt"
    )
    if os.path.exists(CONFIG_LOCATOR_FILE):
        with open(CONFIG_LOCATOR_FILE, "r") as f:
            return f.read().strip()

    return os.path.join(os.getcwd(), "config", "config.ini")


# Cache/Singleton this. The config file does not chang during runtime.
# You should only read the config once at startup anyway
@cache
def get_config(file_path=get_default_config_path()) -> Dict[str, str]:
    """Loads configuration settings from an INI file.

    Args:
        file_path (str): Path to the .ini configuration file.

    Returns:
        dict[str, str]: A dictionary containing configuration settings.
    """
    config = ConfigParser()
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Config file not found: {file_path}")
    config.read(file_path)

    # TODO add range, exisitance and type checks here. Throw errors if not valid.

    return config
