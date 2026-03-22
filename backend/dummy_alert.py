import backend.includes_python.process_logging as slogger
import time

def main():

    slogger.debug("Template Service Debug Test Message")
    slogger.info("Template Service info Test Message")
    slogger.success("Template Service success Test Message")
    slogger.warning("Template Service warning Test Message")
    slogger.error("Template Service  error Test Message")
    slogger.critical("Template Service critical Test Message")
    while True:
        slogger.critical("hello")
        time.sleep(1)


if __name__ == "__main__":
    main()
