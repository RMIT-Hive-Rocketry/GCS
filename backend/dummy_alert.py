import backend.includes_python.process_logging as slogger
import time

def main():

    while True:
        slogger.critical("hello")
        time.sleep(1)


if __name__ == "__main__":
    main()
