import logging
import cli.process as process
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


def start_middleware_build(
    logger: logging.Logger, build_flag: CMakeBuildModes
) -> None:
    if not isinstance(build_flag, CMakeBuildModes):
        raise ValueError(
            f"build_flag must be a CMakeBuildModes value, got: {build_flag} as type {type(build_flag)}"
        )
    service_name = "middleware"
    try:
        if build_flag == CMakeBuildModes.DEBUG:
            build_dir = "build-debug"
        elif build_flag == CMakeBuildModes.RELEASE:
            build_dir = "build-release"

        os.makedirs(build_dir, exist_ok=True)
        cmake_cache_path = Path(build_dir) / "CMakeCache.txt"
        cmake_cache_exists = cmake_cache_path.exists()
        should_configure = not cmake_cache_exists

        os.chdir(build_dir)

        if should_configure:
            middleware_build_command_cmake = [
                "cmake",
                f"-DCMAKE_BUILD_TYPE={build_flag.value}",
                "-DBUILD_TESTS=OFF",
                "..",
            ]

            logger.debug(
                f"Starting {service_name} build [cmake] with: {middleware_build_command_cmake}"
            )

            middleware_build_process_cmake = MiddlewareBuildSubprocess(
                middleware_build_command_cmake,
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

        middleware_build_command_make = [
            "cmake",
            "--build",
            ".",
            "--parallel",
            str(os.cpu_count()),
        ]

        logger.debug(
            f"Starting {service_name} build [cmake --build] with: {middleware_build_command_make}"
        )

        middleware_build_process_make = MiddlewareBuildSubprocess(
            middleware_build_command_make,
            name="cmake-build",
        )
        middleware_build_process_make.start()
        middleware_build_process_make._process.wait()
        if middleware_build_process_make._process.returncode != 0:
            raise RuntimeError("CMake build failed")
        os.chdir("..")  # Back out of build dir
        logger.info("Make build finished")

    except Exception as e:
        logger.error(f"An error occurred while building {service_name}: {e}")
        # Propagate to a blocking handler in cli
        raise
        # return None, None
