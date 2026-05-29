import logging
import re
from typing_extensions import override
from cli import process


class IgnoreWriteMessagesFilter(logging.Filter):
    """Filter to exclude log messages containing 'N write('"""

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        return "N write(" not in record.getMessage()


class SocatSubprocess(process.ERRLoggedSubProcess):
    """Subclass of the ERRLoggedSubProcess with a stop condition for callbacks."""

    @override
    def _update_callback_condition(self) -> bool:
        num_devices = 2
        if self._callback_hits >= num_devices:
            # We only need to read 2 devices from the terminal output. 2 hits is enough
            self._logger_adapter.debug("Stopping socat callbacks")
            self._logger_adapter.debug("Filtering socat write messages")
            self._parent_logger.addFilter(IgnoreWriteMessagesFilter())
            return True
        return False


def device_name_callback(line: str, _stream_name: str) -> str | None:
    """Get the device name/path generated from socat"""

    # Example output from socat.
    # 2025/02/06 20:53:44 socat[56067] N PTY is /dev/ttys012
    # 2025/02/06 20:53:44 socat[56067] N PTY is /dev/ttys016

    # $ echo "Hello Serial" > /dev/ttys012
    # $ echo "Hello Serial" > /dev/ttys012

    # 2025/02/06 21:08:47 socat[56254] N write(7, 0x126814000, 13) completed
    # 2025/02/06 21:08:53 socat[56254] N write(7, 0x126814000, 13) completed

    # Please note that both fake serial devices are linked,
    #   but when you read from one the buffer is cleared
    # That means that you use one as the 'fake device' and the other can just be
    #   for montitoring because nothing will steal the bytes going to it from
    #   the other linked device

    # TODO extract the device names and pass them back to the CLI handler.
    # Then probably start coding the emulator and protobuf?

    if "N PTY is" in line:
        regex_pattern = r"N PTY is (.+)"
        match = re.search(regex_pattern, line)
        if match is None:
            raise RuntimeError("Socat output parsing failed to find device")
        # /dev/ttys012
        return match.group(1)

    return None


def start_fake_serial_device(
    logger: logging.Logger,
) -> tuple[str | None, str | None]:
    """
    Starts a fake serial device using socat and logs the output.
    Returns a tuple containing the paths of the two generated pseudo-terminals.

    Will wait until fake serial termincal have started to return
    """
    try:

        socat_command = [
            "socat",
            "-d",
            "-d",
            "pty,raw,echo=0",
            "pty,raw,echo=0",
        ]
        logger.debug(f"Starting socat with: {socat_command}")
        socat_process = SocatSubprocess(socat_command, name="socat")
        socat_process.register_callback(device_name_callback)

        socat_process.start()

        devices = []
        # Block until both pseudo-terminals are found
        while len(devices) < 2:
            devices += socat_process.get_parsed_data()

        logger.debug(f"Devices found: {devices}")

    except Exception as e:
        logger.error(
            f"An error occurred while starting a Socat fake serial device: {e}"
        )
        return None, None

    return tuple(devices)
