import logging
import cli.process as process
from config.config import get_config
import ipaddress
import socket
import os

# TODO: Implement logging

class IgnoreWebMessagesFilter(logging.Filter):
    """Filter to exclude unneeded web messages"""

    def filter(self, record: logging.LogRecord) -> bool:
        return "GET" not in record.getMessage()


def start_frontend_webserver(logger: logging.Logger, backend_ip = "False"):

    if(backend_ip == "False"):
        logger.info(f"Frontend Webserver running on local device")
    elif(ip_address_validator(backend_ip)):
        logger.info(f"Frontend Webserver running on IP: {backend_ip}")
    else:
        logger.warning(f"Warning incorrect IP passed in frontend Webserver using default IP")

    # If backend IP equals None and passed through to frontend that uses default IP as no clean way to do in python
    env = os.environ.copy()
    env["BACKEND_IP"] = backend_ip

    SERVICE_NAME = "frontend_webserver"
    try:
        FRONTEND_COMMAND = [
            "flask",
            "-A",
            "frontend.server",
            "run",
            "--host=0.0.0.0",
            "--port=8008",
        ]

        logger.debug(f"Starting {SERVICE_NAME} module with: {FRONTEND_COMMAND}")

        frontend_process = process.LoggedSubProcess(
            FRONTEND_COMMAND, name=SERVICE_NAME, env= env, parse_output=False
        )
        frontend_process._parent_logger.addFilter(IgnoreWebMessagesFilter())
        frontend_process.start()

    except Exception as e:
        logger.error(f"An error occurred while starting {SERVICE_NAME}: {e}")
        return None, None
    

def ip_address_validator(ip):
    try:
        ip_obj = ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False