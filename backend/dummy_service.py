import backend.includes_python.process_logging as logger
import backend.includes_python.service_helper as service_helper
import time


def activate_dummy_service():
    logger.info("Starting dummy service")
    while not service_helper.time_to_stop():
        logger.critical(f"hello...")
        time.sleep(1)

    logger.info("Stopped dummy service")


if __name__ == "__main__":
    activate_dummy_service()
