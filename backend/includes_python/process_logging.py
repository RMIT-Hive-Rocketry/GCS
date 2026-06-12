# This is for children processes that log independently of the CLI.

# The CLI will will pipe the logging output from subprocesses to the console.
# This file is just to enforce a consistent logging format across all processes
#   for correct CLI parsing

REGEX_MATCH = r"<(\w{4,8})>:"


def _log(message: str, level: str) -> None:
    print(f"<{level}>:{message}", flush=True)


def debug(message: str) -> None:
    _log(message, "DEBUG")


def info(message: str) -> None:
    _log(message, "INFO")


def success(message: str) -> None:
    _log(message, "SUCCESS")


def warning(message: str) -> None:
    _log(message, "WARNING")


def error(message: str) -> None:
    _log(message, "ERROR")


def critical(message: str) -> None:
    _log(message, "CRITICAL")


# Excluded From Public Frontend
def secret(message: str) -> None:
    _log(message, "SECRET")
