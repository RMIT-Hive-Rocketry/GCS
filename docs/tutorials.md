# How to create a new process / service

This tutorial will help you write your first service for the GCS System!

# General Idea

Services in the GCS are background processes that run alongside and are started by the main `rocket.py` file. Currently some of the existing services include the C++ middleware, The frontend API/WS Server, Pendant Emulator and the Event Viewer. All services are started as a cli process which is started through another python script.

There are 3 key parts of writing a service for the GCS:
1. Write your service in /backend
2. Write a start script in /cli with a function to start your service as a cli process
3. In `rocket.py`'s start_services() call the function you wrote in your service start script.

This setup has a few key benefits, the cli layer allows for true multithreading without being blocked by the python GIL which helps with performance. It also ensures that every service is independent, ensuring if say the frontend crashes it doesn't take down every other service and crash the program with it.

## Tutorial Steps

1. firstly locate the "cli" and "backend" folders inside the codebase.

2. Create a new file in each with the naming conventions used in respective folders.
    > e.g. start_[service-name].py for cli and [service-name].py for backend.

3. Copy inside of each the template code listed below for the respective files.

4. Modify the the first file in the cli folder so that it is linked to the service created in the backend folder.

    >modify the function name to match the format start_[service_name]

    >modify SERVICE_NAME variable to suit the new service name.

    >modify TEMPLATE_SERVICE_COMMAND variable to follow structure of [SERVICE_NAME]_COMMAND

    >modify template_service_process variable to follow structure of [service_name]_process

5.  Customize the service python script to your needs the example script simply uses logging to print out a alert when the script is started however much more is possible then this.

6. to make the service be started and called locate the "start_services()" function inside of [rocket.py](../rocket.py)

7. once found carefully modify the code so that inside the start script the function is called depending on what situation it should run in eg. Dev, Production and in certin modes dictated through the commands. all arguments needed to run should be passed through with the logger argument required.
    > start_template_service(logger)

8. at the top of [rocket.py](../rocket.py) in the includes the starting script inside the cli folder needs to be included. the import name after the file name needs to exactly match the starting function in the service.
    > from cli.start_template_service import start_template_service


##  Key Libraries
The `includes_python` folder contains a couple of useful files that are imported in the template code below. This includes:

- [process_logging.py](../backend/includes_python/process_logging.py) -  which enforces consistent logging format across all processes for correct CLI parsing.
- [service_helper.py](../backend/includes_python/service_helper.py) - which adds signal handlers that allow for correct shut down of the system. For example: when CTRL+C or ESC is detected.

<br><br>
___
___
<br>

# Template Code For New Services.

> ## start_template_service.py
```python
import logging
import cli.process as process
from typing import Tuple
import os

def start_template_service(
    logger: logging.Logger
):
    SERVICE_NAME = "template service"
    try:

        TEMPLATE_SERVICE_COMMAND = [
            "python3",
            os.path.join("backend", "template_service.py"),
            "-u",
        ]

        logger.debug(f"Starting {SERVICE_NAME}")

        # Set PYTHONPATH to the project root to ensure imports work correctly.
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        template_service_process = process.LoggedSubProcess(
            DUMMY_ALERT_COMMAND, name=SERVICE_NAME, env=env, parse_output=True
        )

        template_service_process.start()

    except Exception as e:
        logger.error(f"An error occurred while starting {SERVICE_NAME}: {e}")
        return None, None

```


> ## template_service.py
```python
import backend.includes_python.process_logging as slogger
import backend.includes_python.service_helper as service_helper
import time

# Run Service Code Here Eg Send One Time Alive Message
def main():
    slogger.debug("Template Service Debug Test Message")
    slogger.info("Template Service info Test Message")
    slogger.success("Template Service success Test Message")
    slogger.warning("Template Service warning Test Message")
    slogger.error("Template Service error Test Message")
    slogger.critical("Template Service critical Test Message")

    # the while loop continues until the signal from the process handler tells to stop
    while not service_helper.time_to_stop()::
        # Do Nothing But Wait
        time.sleep(1)

if __name__ == "__main__":
    main()
```
