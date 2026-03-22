import backend.includes_python.process_logging as logger
import backend.includes_python.service_helper as service_helper
from time import sleep

def dummy_service():
    logger.info("Dummy service started")
    while not service_helper.time_to_stop():
        logger.critical("Hello From Dummy Service!!!!")
        sleep(1)
    logger.info("Dummy Service Exiting, Bye!")

if __name__ == "__main__":
    dummy_service()