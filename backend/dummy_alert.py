import backend.includes_python.process_logging as slogger
import backend.includes_python.service_helper as service_helper
import time

def main():

    while not service_helper.time_to_stop():
        slogger.critical("hello")
        time.sleep(1)


if __name__ == "__main__":
    main()
