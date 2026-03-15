import logging
import cli.proccess as process
from enum import Enum
import os
from pathlib import Path


class CMakeBuildModes(Enum):
    DEBUG = "Debug"
    RELEASE = "Release"


class MiddlewareBuildSubprocess(process.LoggedSubProcess):
    """Subclass of LoggedSubProcess with a stop condition for callbacks."""

    def _update_callback_condition(self) -> bool:
        if self._callback_hits >= 1:
            self._logger_adapter.debug(
                "Stopping build callbacks for this process"
            )
            return True
        return False


def start_middleware_build(logger: logging.Logger, BUILD_FLAG: CMakeBuildModes):
    if not isinstance(BUILD_FLAG, CMakeBuildModes):
        raise ValueError(
            f"BUILD_FLAG must be a CMakeBuildModes value, got: {BUILD_FLAG} as type {type(BUILD_FLAG)}"
        )
    SERVICE_NAME = "middleware"
    try:
        if BUILD_FLAG == CMakeBuildModes.DEBUG:
            BUILD_DIR = "build-debug"
        elif BUILD_FLAG == CMakeBuildModes.RELEASE:
            BUILD_DIR = "build-release"

        os.makedirs(BUILD_DIR, exist_ok=True)
        cmake_cache_path = Path(BUILD_DIR) / "CMakeCache.txt"
        cmake_cache_exists = cmake_cache_path.exists()
        should_configure = not cmake_cache_exists

        os.chdir(BUILD_DIR)

        if should_configure:
            MIDDLEWARE_BUILD_COMMAND_CMAKE = [
                "cmake",
                f"-DCMAKE_BUILD_TYPE={BUILD_FLAG.value}",
                "..",
            ]

            logger.debug(
                f"Starting {SERVICE_NAME} build [cmake] with: {MIDDLEWARE_BUILD_COMMAND_CMAKE}"
            )

            middleware_build_process_cmake = MiddlewareBuildSubprocess(
                MIDDLEWARE_BUILD_COMMAND_CMAKE,
                name="cmake",
            )
            middleware_build_process_cmake.start()
            middleware_build_process_cmake._process.wait()
            if middleware_build_process_cmake._process.returncode != 0:
                raise RuntimeError("CMake configure failed")
            logger.info("CMake configure finished")
        else:
            logger.info("Skipping CMake configure: cache is current")

        # ---- Start make ----

        MIDDLEWARE_BUILD_COMMAND_MAKE = [
            "cmake",
            "--build",
            ".",
            "--parallel",
            str(os.cpu_count()),
        ]

        logger.debug(
            f"Starting {SERVICE_NAME} build [cmake --build] with: {MIDDLEWARE_BUILD_COMMAND_MAKE}"
        )

        middleware_build_process_make = MiddlewareBuildSubprocess(
            MIDDLEWARE_BUILD_COMMAND_MAKE,
            name="cmake-build",
        )
        middleware_build_process_make.start()
        middleware_build_process_make._process.wait()
        if middleware_build_process_make._process.returncode != 0:
            raise RuntimeError("CMake build failed")
        os.chdir("..")  # Back out of build dir
        logger.info("Make build finished")

    except Exception as e:
        logger.error(f"An error occurred while building {SERVICE_NAME}: {e}")
        # Propogate to a blocking handler in cli
        raise
        # return None, None
