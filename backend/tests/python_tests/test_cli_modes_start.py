import subprocess
import sys
import os
import time
import threading
import queue
import pytest
from abc import abstractmethod, ABC
import re


class ProcessOutputScanner:
    """Handles scanning process output for success/failure patterns."""

    def __init__(self, output_queue: queue.Queue):
        self.output_queue = output_queue
        self.captured_lines = []

    def scan_for_patterns(
        self, fail_any: list[str], success_all: list[str], timeout: float = 10.0
    ) -> tuple[bool, list[str]]:
        """
        Scans output for failure/success patterns using regex.

        Args:
            fail_any: List of regex patterns - if any match, test fails
            success_all: List of regex patterns - all must match to succeed
            timeout: How long to wait for patterns

        Returns:
            Tuple of (success: bool, captured_lines: List[str])
        """
        start_time = time.time()
        success_targets = set(success_all)

        # Compile regex patterns for better performance
        fail_regexes = [re.compile(pattern) for pattern in fail_any]
        success_regexes = {
            pattern: re.compile(pattern) for pattern in success_all
        }

        while time.time() - start_time < timeout:
            try:
                line = self.output_queue.get(timeout=0.1)
                self.captured_lines.append(line)
                print(line)  # debugging: stream process output

                for fail_regex in fail_regexes:
                    if fail_regex.search(line):
                        print(
                            "\n\nFailure pattern matched:", line, end="\n\n\n"
                        )
                        failure_time = time.time()
                        while time.time() - failure_time < 1:
                            # Print traceback for 1 second
                            try:
                                line = self.output_queue.get(timeout=0.1)
                            except queue.Empty:
                                pass  # Just busy ask for new lines
                            self.captured_lines.append(line)
                            print(line)
                        return False, self.captured_lines

                for success_pattern in list(success_targets):
                    if success_regexes[success_pattern].search(line):
                        success_targets.remove(success_pattern)

                if len(success_targets) == 0:
                    return True, self.captured_lines

            except queue.Empty:
                continue
        else:
            print("Timeout reached without matching all success patterns.")
            print("Remaining success patterns:", success_targets)
            return False, self.captured_lines


class ProcessResourceMonitor:
    """Polls process resources and stores peak memory and CPU usage."""

    def __init__(self, pid: int, sample_interval_s: float = 0.25):
        self.pid = pid
        self.sample_interval_s = sample_interval_s
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.peak_rss_kb = 0
        self.peak_cpu_pct = 0.0
        self.samples_taken = 0

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._monitor,
            daemon=True,
            name=f"resource-monitor-{self.pid}",
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1)

    def snapshot(self) -> dict[str, int | float]:
        return {
            "peak_rss_kb": self.peak_rss_kb,
            "peak_rss_mb": self.peak_rss_kb / 1024,
            "peak_cpu_pct": self.peak_cpu_pct,
            "samples_taken": self.samples_taken,
        }

    def _monitor(self) -> None:
        # We use `ps` to avoid adding a test dependency like psutil.
        while not self._stop_event.is_set():
            sample = self._sample_ps()
            if sample is not None:
                rss_kb, cpu_pct = sample
                self.samples_taken += 1
                self.peak_rss_kb = max(self.peak_rss_kb, rss_kb)
                self.peak_cpu_pct = max(self.peak_cpu_pct, cpu_pct)
            self._stop_event.wait(self.sample_interval_s)

    def _sample_ps(self) -> tuple[int, float] | None:
        result = subprocess.run(
            ["ps", "-o", "rss=", "-o", "%cpu=", "-p", str(self.pid)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        lines = result.stdout.strip().splitlines()
        if not lines:
            return None

        parts = lines[-1].split()
        if len(parts) < 2:
            return None

        try:
            rss_kb = int(parts[0])
            cpu_pct = float(parts[1])
        except ValueError:
            return None

        return rss_kb, cpu_pct


class CliStartup(ABC):
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../.."))
    DEFAULT_FAIL_PATTERNS = [
        r"\[STDERR\](?!.*(?:This is a development server|Running on|Press CTRL\+C to quit)).*",
        r"Traceback \(most recent call last\)",
    ]
    # Note that these patterns must match the detailed_logging_prefix logs
    # See config.ini
    DEFAULT_SUCCESS_PATTERNS = [
        "Starting Soteria",
        "socat: Stopping socat callbacks",  # found devices
        r"server: \[STDOUT] Starting middleware server",
        r"server: \[STDOUT] Interface \[GSE] initialised with type: TEST*",
        r"server: \[STDOUT] Interface  \[AV] reusing GSE interface \(same type/path\)",
        r"event viewer: \[STDOUT] Listening for messages\.\.\.",
        r"event viewer: \[STDOUT] Supersonic flight detected",
    ]
    MAX_RSS_MB = float(os.getenv("ROCKET_TEST_MAX_RSS_MB", "100"))
    # increase this to fix flakey tests. It only exists to find runaway programs
    MAX_CPU_PCT = float(os.getenv("ROCKET_TEST_MAX_CPU_PCT", "50"))

    # Protected
    def _start_process(self, ROCKET_ARGS: list):
        if ROCKET_ARGS is None:
            raise NotImplementedError(
                "ROCKET_ARGS must be provided for your test class"
            )

        cmd = [sys.executable, "-u", "rocket.py"]
        cmd.extend(ROCKET_ARGS)

        if "run" not in ROCKET_ARGS and "--nobuild" not in cmd:
            print(f"ROCKET_ARGS: {ROCKET_ARGS}")
            raise ValueError(
                "ROCKET_ARGS must include --nobuild for your non release test class"
            )

        CLI_FILE_PATH = os.path.join(CliStartup.PROJECT_ROOT, "rocket.py")
        print(f"Expected rocket.py path: {CLI_FILE_PATH}")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            text=True,
            cwd=CliStartup.PROJECT_ROOT,
        )

        assert proc.pid and proc.pid > 0

        output_queue = queue.Queue()
        resource_monitor = ProcessResourceMonitor(proc.pid)
        resource_monitor.start()

        def _monitor_stream(stream, q):
            for line in iter(stream.readline, ""):
                q.put(line.strip())
            stream.close()

        thread = threading.Thread(
            target=_monitor_stream,
            args=(proc.stdout, output_queue),
            daemon=True,
        )
        thread.start()

        # Send test the process and the output queue after fixture setup
        scanner = ProcessOutputScanner(output_queue)
        yield proc, scanner, resource_monitor

        # Automatic cleanup (if test didn't already kill it)
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

        resource_monitor.stop()
        thread.join(timeout=1)

    @pytest.fixture(scope="class")
    def process_and_scanner(self, request):
        """Call `_start_process` with appropriate args and return the process and scanner"""
        rocket_args = self.get_rocket_args()
        gen = self._start_process(rocket_args)
        proc, scanner, resource_monitor = next(gen)
        yield proc, scanner, resource_monitor
        try:
            next(gen)
        except StopIteration:
            pass

    def assert_resource_limits(self, resource_monitor: ProcessResourceMonitor):
        stats = resource_monitor.snapshot()
        assert stats["peak_rss_mb"] <= self.MAX_RSS_MB, (
            f"Peak RSS {stats['peak_rss_mb']:.2f}MB exceeded "
            f"ROCKET_TEST_MAX_RSS_MB={self.MAX_RSS_MB:.2f}MB"
        )
        assert stats["peak_cpu_pct"] <= self.MAX_CPU_PCT, (
            f"Peak CPU {stats['peak_cpu_pct']:.2f}% exceeded "
            f"ROCKET_TEST_MAX_CPU_PCT={self.MAX_CPU_PCT:.2f}%"
        )
        print(
            "Peak usage: "
            f"{stats['peak_rss_mb']:.2f}MB RSS, "
            f"{stats['peak_cpu_pct']:.2f}% CPU, "
            f"{stats['samples_taken']} samples"
        )

    @abstractmethod
    def get_rocket_args(self) -> list[str]:
        """Return the rocket.py arguments for this test class."""


@pytest.mark.skipif(
    os.getenv("CI_BUILD_ENV") != "Debug",
    reason="CI_BUILD_ENV undefined or not Debug",
)
class TestDevStartups(CliStartup):
    def get_rocket_args(self) -> list[str]:
        return [
            "dev",
            "--interface",
            "test",
            "--nopendant",
            "--nobuild",
            "--frontend",
        ]

    def test_runs_successfully(
        self,
        process_and_scanner: tuple[
            subprocess.Popen, ProcessOutputScanner, ProcessResourceMonitor
        ],
    ):
        proc, scanner, resource_monitor = process_and_scanner
        fail_patterns = CliStartup.DEFAULT_FAIL_PATTERNS
        success_patterns = CliStartup.DEFAULT_SUCCESS_PATTERNS + [
            r"device emulator: \[STDOUT] Emulator starting",
            r"WebSocket server started at",
            r"\* Serving Flask app 'frontend\.server'",
        ]
        success, output_lines = scanner.scan_for_patterns(
            fail_any=fail_patterns, success_all=success_patterns, timeout=30.0
        )
        assert success, "System failed to match patterns"
        self.assert_resource_limits(resource_monitor)
        print(f"System ran successfully. Captured {len(output_lines)} lines")


@pytest.mark.skipif(
    os.getenv("CI_BUILD_ENV") != "Run",
    reason="CI_BUILD_ENV undefined or not Run",
)
class TestRunStartups(CliStartup):
    def get_rocket_args(self) -> list[str]:
        return ["run"]

    def test_runs_successfully(
        self,
        process_and_scanner: tuple[
            subprocess.Popen, ProcessOutputScanner, ProcessResourceMonitor
        ],
    ):
        proc, scanner, resource_monitor = process_and_scanner
        fail_patterns = CliStartup.DEFAULT_FAIL_PATTERNS
        # Do not test any further until you have super sexy test cases for it
        # Run is a subset of the dev mode anyway. Most of it will be covered
        # The only thing this really misses is the physical interface testing
        success_patterns = [
            r"------- STARTING SOTERIA IN PRODUCTION MODE -------",
            r"Release python testing is not implemented",
        ]
        success, output_lines = scanner.scan_for_patterns(
            fail_any=fail_patterns, success_all=success_patterns, timeout=30.0
        )
        assert success, "System failed to match patterns"
        self.assert_resource_limits(resource_monitor)
        print(f"System ran successfully. Captured {len(output_lines)} lines")


@pytest.mark.skipif(
    os.getenv("CI_BUILD_ENV") != "Debug",
    reason="CI_BUILD_ENV undefined or not Debug",
)
class TestInterfaceUART_E5(CliStartup):
    def get_rocket_args(self) -> list[str]:
        return [
            "dev",
            "--interface",
            "TEST_UART_E5",
            "--nopendant",
            "--nobuild",
            "--frontend",
        ]

    def test_runs_successfully(
        self,
        process_and_scanner: tuple[
            subprocess.Popen, ProcessOutputScanner, ProcessResourceMonitor
        ],
    ):
        proc, scanner, resource_monitor = process_and_scanner
        fail_patterns = CliStartup.DEFAULT_FAIL_PATTERNS
        success_patterns = CliStartup.DEFAULT_SUCCESS_PATTERNS + [
            r"device emulator: \[STDOUT] Emulator starting",
            r"WebSocket server started at",
            r"\* Serving Flask app 'frontend\.server'",
        ]
        success, output_lines = scanner.scan_for_patterns(
            fail_any=fail_patterns, success_all=success_patterns, timeout=30.0
        )
        assert success, "System failed to match patterns"
        self.assert_resource_limits(resource_monitor)
        print(f"System ran successfully. Captured {len(output_lines)} lines")


@pytest.mark.skipif(os.getenv("CI_BUILD_ENV") != "Debug", reason="CI_BUILD_ENV undefined or not Debug")
# See logs from https://github.com/RMIT-Hive-Rocketry/GCS-2026/commit/dcd83d77b575807498cad0bbb10d35e56eecb06c
@pytest.mark.skip(reason="Skipped until rocketpy supports new API format")
class TestReplaySimulationStartups(CliStartup):
    def get_rocket_args(self) -> list[str]:
        return [
            "replay",
            "--mode",
            "simulation",
            "--simulation",
            "test",
            "--nobuild",
        ]

    def test_runs_successfully(
        self,
        process_and_scanner: tuple[
            subprocess.Popen, ProcessOutputScanner, ProcessResourceMonitor
        ],
    ):
        proc, scanner, resource_monitor = process_and_scanner
        fail_patterns = CliStartup.DEFAULT_FAIL_PATTERNS
        success_patterns = CliStartup.DEFAULT_SUCCESS_PATTERNS + [
            r"replay system: \[STDOUT] Starting simulation replay for TEST",
        ]
        success, output_lines = scanner.scan_for_patterns(
            fail_any=fail_patterns, success_all=success_patterns, timeout=30.0
        )
        assert success, "System failed to match patterns"
        self.assert_resource_limits(resource_monitor)
        print(f"System ran successfully. Captured {len(output_lines)} lines")


@pytest.mark.skipif(
    os.getenv("CI_BUILD_ENV") != "Debug",
    reason="CI_BUILD_ENV undefined or not Debug",
)
@pytest.mark.skip(reason="Skipped until rocketpy supports new API format")
class TestReplayMissionStartups(CliStartup):
    def get_rocket_args(self) -> list[str]:
        return [
            "replay",
            "--mode",
            "mission",
            "--mission",
            "20250504",
            "--nobuild",
        ]

    def test_runs_successfully(
        self,
        process_and_scanner: tuple[
            subprocess.Popen, ProcessOutputScanner, ProcessResourceMonitor
        ],
    ):
        proc, scanner, resource_monitor = process_and_scanner
        fail_patterns = CliStartup.DEFAULT_FAIL_PATTERNS
        success_patterns = CliStartup.DEFAULT_SUCCESS_PATTERNS + [
            r"replay system: \[STDOUT] BAD GYRO_Y=400.80500000715256 ENTRY DETECTED CAPPING VALUE",
        ]
        success, output_lines = scanner.scan_for_patterns(
            fail_any=fail_patterns, success_all=success_patterns, timeout=30.0
        )
        assert success, "System failed to match patterns"
        self.assert_resource_limits(resource_monitor)
        print(f"System ran successfully. Captured {len(output_lines)} lines")


@pytest.mark.skipif(
    os.getenv("CI_BUILD_ENV") != "Debug",
    reason="CI_BUILD_ENV undefined or not Debug",
)
@pytest.mark.skip(reason="Skipped until rocketpy supports")
class TestDemoMissionStartups(CliStartup):
    def get_rocket_args(self) -> list[str]:
        return [
            "replay",
            "--mode",
            "simulation",
            "--simulation",
            "demo",
            "--nobuild",
        ]

    def test_runs_successfully(
        self,
        process_and_scanner: tuple[
            subprocess.Popen, ProcessOutputScanner, ProcessResourceMonitor
        ],
    ):
        proc, scanner, resource_monitor = process_and_scanner
        fail_patterns = CliStartup.DEFAULT_FAIL_PATTERNS
        success_patterns = CliStartup.DEFAULT_SUCCESS_PATTERNS + [
            r"replay system: \[STDOUT] STARTING UP DEMO MODE, THIS WILL RUN UNTIL STOPPED",
        ]
        success, output_lines = scanner.scan_for_patterns(
            fail_any=fail_patterns, success_all=success_patterns, timeout=30.0
        )
        assert success, "System failed to match patterns"
        self.assert_resource_limits(resource_monitor)
        print(f"System ran successfully. Captured {len(output_lines)} lines")
