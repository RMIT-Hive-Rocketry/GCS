import os
import backend.includes_python.process_logging as slogger
import time
import sys
import platform
from dataclasses import dataclass
from config.config import get_config
import ast
import csv
import backend.includes_python.service_helper as service_helper


START_TIME = None  # init in start

# Windows Integration
if platform.system() == "Windows":
    import ctypes
    from ctypes import wintypes

    class FileTime(ctypes.Structure):
        _fields_ = [
            ("dwLowDateTime", ctypes.c_uint32),
            ("dwHighDateTime", ctypes.c_uint32),
        ]

    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

elif platform.system() == "Darwin":
    import subprocess

    import ctypes
    from ctypes import c_uint

    libc = ctypes.CDLL("libc.dylib")

    HOST_CPU_LOAD_INFO = 3
    CPU_STATE_MAX = 4
    TICK_RATE = 100

    PROC_PIDTASKINFO = 4  # macOS constant

    class ProcessTaskInfo(ctypes.Structure):
        _fields_ = [
            ("pti_virtual_size", ctypes.c_uint64),
            ("pti_resident_size", ctypes.c_uint64),
            ("pti_total_user", ctypes.c_uint64),
            ("pti_total_system", ctypes.c_uint64),
            ("pti_threads_user", ctypes.c_uint64),
            ("pti_threads_system", ctypes.c_uint64),
            ("pti_policy", ctypes.c_int),
            ("pti_faults", ctypes.c_int),
            ("pti_pageins", ctypes.c_int),
            ("pti_cow_faults", ctypes.c_int),
            ("pti_messages_sent", ctypes.c_int),
            ("pti_messages_received", ctypes.c_int),
            ("pti_syscalls_mach", ctypes.c_int),
            ("pti_syscalls_unix", ctypes.c_int),
            ("pti_csw", ctypes.c_int),
            ("pti_threadnum", ctypes.c_int),
            ("pti_numrunning", ctypes.c_int),
            ("pti_priority", ctypes.c_int),
        ]

    class HostCPULoadInfoDataT(ctypes.Structure):
        _fields_ = [("cpu_ticks", c_uint * CPU_STATE_MAX)]

elif platform.system() == "Linux":
    pass
else:
    slogger.error(
        "Performance Monitor Is not Supported On this OS please use Linux Or Windows !"
    )
    sys.exit("Invalid OS")

# Got most of declarations from https://docs.kernel.org/filesystems/proc.html


@dataclass
class GlobalSystemInfo:
    user_time: float
    kernel_time: float
    idle_time: float
    other_time: float  # Includes involuntary waits IRQ, etc

    used_time: float
    used_time_delta: float
    cpu_usage_percent: float

    vm_rss: int  # total system ram usage
    total_mem: int  # total system ram cap


@dataclass
class ProcessSystemData:
    pid: int
    name: str

    vm_rss: int  # Ram Usage For The Process (kB)
    cpu_util_percent: float
    mem_util_percent: float

    user_time: float  # Time in Jiffies / ticks in user mode
    kernel_time: float  # Time in Jiffies / ticks in kernel mode
    cpu_usage_time: float

    delta_user_time: float  # Time in Jiffies / ticks in user mode
    delta_kernel_time: float  # Time in Jiffies / ticks in kernel mode
    delta_cpu_usage_time: float


def filetime_to_int(ft) -> int:
    return (ft.dwHighDateTime << 32) + ft.dwLowDateTime


# Extract from the proc Directory the details needed
def get_process_status_linux(pid) -> ProcessSystemData:
    process_data = ProcessSystemData(pid, "", 0, 0, 0, 0, 0, 0, 0, 0, 0)
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    process_data.vm_rss = int(line.split()[1])

        with open(f"/proc/{pid}/stat") as f:
            stat_cont = f.read().split()

            process_data.user_time = int(
                stat_cont[13]
            )  # Index within the files
            process_data.kernel_time = int(stat_cont[14])
            process_data.cpu_usage_time = (
                process_data.user_time + process_data.kernel_time
            )

        return process_data

    except FileNotFoundError:
        slogger.error(f"couldn't Access {pid}")
        return None
    except Exception as e:
        slogger.error(f"Process Logging Failed to execute {e}")
        return None


# Extract from the proc Directory the details needed meminfo
def get_global_status_linux() -> GlobalSystemInfo:
    sys_info = GlobalSystemInfo(0, 0, 0, 0, 0, 0, 0, 0, 0)
    try:
        with open("/proc/stat") as f:
            for line in f:
                if line.startswith("cpu"):
                    system_list = line.split()
                    sys_info.user_time = int(system_list[1]) + int(
                        system_list[2]
                    )  # User Global Time + User Nice Time
                    sys_info.kernel_time = int(system_list[3])
                    sys_info.idle_time = int(system_list[4]) + int(
                        system_list[5]
                    )
                    sys_info.other_time = (
                        int(system_list[6])
                        + int(system_list[7])
                        + int(system_list[8])
                        + int(system_list[9])
                        + int(system_list[10])
                    )  # irq, softirq, steal, guest, guest_niced

                    sys_info.used_time = (
                        sys_info.user_time
                        + sys_info.kernel_time
                        + sys_info.other_time
                    )
                    break

        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    sys_info.total_mem = int(line.split()[1])

                if line.startswith("MemAvailable"):
                    sys_info.vm_rss = sys_info.total_mem - int(
                        line.split()[1]
                    )  # Used Memory equals the total memory - available to get most accurate

    except FileNotFoundError:
        slogger.error("Process Not Found")
        return sys_info

    except Exception as e:
        slogger.error(f"Process Logging Failed to execute {e}")
        return sys_info

    return sys_info


# Extract from the proc Directory the details needed
def get_process_status_windows(pid) -> ProcessSystemData:

    psapi = ctypes.WinDLL("psapi.dll")
    kernel32 = ctypes.WinDLL("kernel32.dll")

    process_data = ProcessSystemData(pid, "", 0, 0, 0, 0, 0, 0, 0)

    process_query_limited_information = 0x1000
    # PROCESS_VM_READ = 0x0010 Might Need In future

    # Get process of kernel info with perms and for a specific PID
    handle = kernel32.OpenProcess(process_query_limited_information, False, pid)

    if not handle:
        slogger.error("Invalid Hook")
        return None

    creation = FileTime()
    exit_time = FileTime()
    kernel = FileTime()
    user = FileTime()

    kernel32.GetProcessTimes(
        handle,
        ctypes.byref(creation),
        ctypes.byref(exit_time),
        ctypes.byref(kernel),
        ctypes.byref(user),
    )

    process_data.user_time = filetime_to_int(user)
    process_data.kernel_time = filetime_to_int(kernel)
    process_data.cpu_usage_time = (
        process_data.user_time + process_data.kernel_time
    )

    # Memory Segment

    if not handle:
        slogger.error("Could not open process")
        return None

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(ProcessMemoryCounters)

    psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)

    kernel32.CloseHandle(handle)
    process_data.vm_rss = counters.WorkingSetSize

    return process_data


def get_global_status_windows() -> GlobalSystemInfo:
    sys_info = GlobalSystemInfo(0, 0, 0, 0, 0, 0)
    kernel32 = ctypes.WinDLL("kernel32.dll")
    idle = FileTime()
    kernel = FileTime()
    user = FileTime()

    kernel32.GetSystemTimes(
        ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
    )

    # Convert Propritary Windows file time to seconds
    sys_info.idle_time = filetime_to_int(idle)
    sys_info.kernel_time = filetime_to_int(kernel)
    sys_info.user_time = filetime_to_int(user)
    sys_info.used_time = sys_info.user_time + sys_info.kernel_time

    x = MemoryStatusEx()
    x.dwLength = ctypes.sizeof(MemoryStatusEx)

    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(x))

    sys_info.total_mem = x.ullTotalPhys
    sys_info.vm_rss = x.ullTotalPhys - x.ullAvailPhys

    return sys_info


# Extract from the proc Directory the details needed
def get_process_status_mac(pid) -> ProcessSystemData:
    process_data = ProcessSystemData(pid, "", 0, 0, 0, 0, 0, 0, 0, 0, 0)

    info = ProcessTaskInfo()

    size = libc.proc_pidinfo(
        pid, PROC_PIDTASKINFO, 0, ctypes.byref(info), ctypes.sizeof(info)
    )

    if size <= 0:
        slogger.error(f"Unable to access Process Info: {pid}")
        return None

    # CPU times are in nanoseconds
    user_time = info.pti_total_user
    system_time = info.pti_total_system

    rss = info.pti_resident_size  # bytes

    process_data.user_time = int(user_time)
    process_data.kernel_time = int(system_time)
    process_data.vm_rss = int(rss) / 1000  # Bytes to KB
    process_data.cpu_usage_time = int(process_data.user_time) + int(
        process_data.kernel_time
    )
    return process_data


def get_global_status_mac() -> GlobalSystemInfo:
    sys_info = GlobalSystemInfo(0, 0, 0, 0, 0, 0, 0, 0, 0)

    cpu_info = HostCPULoadInfoDataT()

    # Calculates the expected size of the struct for the kernel to fill
    count = ctypes.c_uint(ctypes.sizeof(cpu_info) // ctypes.sizeof(c_uint))

    clock_tick = os.sysconf(
        "SC_clock_tick"
    )  # Get Current Tick rate to convert to ns

    ret = libc.host_statistics64(
        libc.mach_host_self(),
        HOST_CPU_LOAD_INFO,
        ctypes.byref(cpu_info),
        ctypes.byref(count),
    )

    user = cpu_info.cpu_ticks[0]
    system = cpu_info.cpu_ticks[1]
    idle = cpu_info.cpu_ticks[2]

    # Convert Internal Schedular ticks to ns
    sys_info.idle_time = idle * (1e9 / clock_tick)
    sys_info.kernel_time = system * (1e9 / clock_tick)
    sys_info.user_time = user * (1e9 / clock_tick)
    sys_info.used_time = sys_info.user_time + sys_info.kernel_time

    ### Memory

    # this script creates a subprocess with the command vm_stat and parses the data to get what is needed

    memory_data = subprocess.check_output(["vm_stat"]).decode()

    lines = memory_data.split("\n")
    vm = {}

    # if line doesn't contain a ":" then it doesn't contain data
    for line in lines:
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        # extract leading number only letters from the numbers
        num = ""
        for c in value:
            if c.isdigit():
                num += c
            else:
                break

        if num:
            vm[key] = int(num)

    page_size = 4096  # bytes (default on macOS)

    free = vm.get("Pages free", 0) * page_size
    inactive = vm.get("Pages inactive", 0) * page_size
    active = vm.get("Pages active", 0) * page_size
    wired = vm.get("Pages wired down", 0) * page_size

    sys_info.total_mem = free + inactive + active + wired
    sys_info.vm_rss = active + wired

    return sys_info


def get_process_status(pid) -> ProcessSystemData:
    if platform.system() == "Windows":
        return get_process_status_windows(pid)
    if platform.system() == "Linux":
        return get_process_status_linux(pid)
    if platform.system() == "Darwin":
        return get_process_status_mac(pid)
    return None


def get_global_status() -> GlobalSystemInfo:
    if platform.system() == "Windows":
        return get_global_status_windows()
    if platform.system() == "Linux":
        return get_global_status_linux()
    if platform.system() == "Darwin":
        return get_global_status_mac()
    return None


def main() -> None:

    # Get Arguments and Parse
    service_list = sys.argv[sys.argv.index("--running_services") + 1]

    global START_TIME
    START_TIME = sys.argv[sys.argv.index("--START_TIME") + 1]

    if service_list is None:
        slogger.error(
            "Please Enter a valid argument e.g. --running_services [(pid1,name1), (pid2,name2)]"
        )
        return

    if START_TIME is None:
        slogger.error(
            "Please Enter a valid argument e.g. --START_TIME from time.perf_counter()"
        )
        return

    try:
        processes_data_list = ast.literal_eval(service_list)
    except Exception:
        slogger.error(
            "running_services argument invalid e.g. --running_services [(pid1,name1), (pid2,name2)]"
        )
        return

    previous_sys_data = get_global_status()
    our_previous_sys_data = [
        get_process_status(active_process[0])
        for active_process in processes_data_list
    ]

    # Get Config File and genurate location for the new performance logging log files
    config = get_config()
    log_dir_path = config["performance_monitor"]["performance_log_dir"].strip()
    sampling_interval = float(
        config["performance_monitor"]["performance_sampling_interval"].strip()
    )

    # Keep Track of loops to show logs to cli
    loop_count = 0
    cli_log_threshold = int(
        config["performance_monitor"]["performance_cli_log_interval"].strip()
    )

    log_filename = f"performance_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    log_file_path = os.path.join(log_dir_path, log_filename)

    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    # Prepare Log Header
    headers = [
        "unix_time",
        "timestamp",
        "total_ram_percent",
        "our_ram_percent",
        "total_cpu_percent",
        "our_cpu_percent",
    ]

    for i in range(len(processes_data_list)):
        headers += [f"pid_{i}", f"name_{i}", f"cpu_{i}", f"mem_{i}", f"rss_{i}"]

    with open(log_file_path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)

    # Sleep To Give Initial Data time to change
    time.sleep(sampling_interval)

    while service_helper.time_to_stop() != True:
        loop_count += 1

        # Call function to get global system data
        system_data = get_global_status()

        # Calculate Values from the global data
        total_time = (
            system_data.user_time
            + system_data.idle_time
            + system_data.kernel_time
            + system_data.other_time
        )
        total_time_delta = total_time - (
            previous_sys_data.user_time
            + previous_sys_data.idle_time
            + previous_sys_data.kernel_time
            + previous_sys_data.other_time
        )
        # idle_timeDelta = system_data.idle_time - (previous_sys_data.idle_time) Maybe useful

        system_data.used_time_delta = (
            system_data.used_time - previous_sys_data.used_time
        )

        # Global Values our services resource use
        our_ram_use = 0
        our_cpu_use = 0
        our_sys_data: ProcessSystemData = []

        for idx, active_process in enumerate(processes_data_list):
            # Get Memory Data For Process
            ps = get_process_status(active_process[0])

            if ps is None or (
                ps.vm_rss == 0
                and ps.cpu_usage_time
                == our_previous_sys_data[idx].cpu_usage_time
            ):
                slogger.warning(
                    f"Service {active_process[1]} Cannot Be Accessed No Longer Logging"
                )
                processes_data_list.pop(idx)
                continue

            # Countinus Addition of ram usage percent across system
            our_ram_use += +ps.vm_rss

            ps.mem_util_percent = ps.vm_rss / system_data.total_mem

            # Assign Individual deltas to the processes
            ps.delta_kernel_time = (
                ps.kernel_time - our_previous_sys_data[idx].kernel_time
            )
            ps.delta_user_time = (
                ps.user_time - our_previous_sys_data[idx].user_time
            )

            ps.delta_cpu_usage_time = (
                ps.cpu_usage_time - our_previous_sys_data[idx].cpu_usage_time
            )

            # Total Current CpuUse cycles added across all monitored processes
            our_cpu_use += ps.delta_cpu_usage_time

            # map indiviudal utilisation to each processes
            if total_time_delta != 0:
                ps.cpu_util_percent = (
                    ps.delta_cpu_usage_time / total_time_delta
                ) * 100
            else:
                ps.cpu_util_percent = 0

            # Add pid and name into the process info that was passed initially from args
            ps.pid = active_process[0]
            ps.name = active_process[1]

            our_sys_data.append(ps)

        if total_time_delta != 0:
            our_cpu_use_percent = (our_cpu_use / total_time_delta) * 100
            system_data.cpu_usage_percent = (
                system_data.used_time_delta / total_time_delta
            ) * 100
        else:
            our_cpu_use_percent = 0
            system_data.cpu_usage_percent = 0

        our_ram_use_percent = (our_ram_use / system_data.total_mem) * 100
        total_ram_use_percent = (
            system_data.vm_rss / system_data.total_mem
        ) * 100

        # Gen dynamic rows for each service
        row = [
            round(time.time(), 3),
            str(round(time.perf_counter() - float(START_TIME), 3)),
            round(total_ram_use_percent, 3),
            round(our_ram_use_percent, 7),
            round(system_data.cpu_usage_percent, 7),
            round(our_cpu_use_percent, 7),
        ]

        # Generate dynamic string of processes and details to append onto log
        for osd in our_sys_data:
            row.extend(
                [
                    osd.pid,
                    osd.name,
                    round(osd.cpu_util_percent, 7),
                    round(osd.mem_util_percent, 5),
                    round(osd.vm_rss, 2),
                ]
            )

        with open(log_file_path, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(row)

        # This is in seconds as one loop executes every second
        if loop_count >= cli_log_threshold:
            slogger.debug(
                f"System CPU Util: {round(system_data.cpu_usage_percent,2)}% Ram Util: {round(total_ram_use_percent,2)}%"
            )
            slogger.debug(
                f"Program CPU Util: {round(our_cpu_use_percent,2)}% Ram Util: {round(our_ram_use_percent,2)}%"
            )
            loop_count = 0

        # Update Old Values with current ones
        previous_sys_data = system_data

        our_previous_sys_data.clear()
        our_previous_sys_data = [
            get_process_status(active_process[0])
            for active_process in processes_data_list
        ]

        # Wait For Next sampling Interval
        time.sleep(sampling_interval)


if __name__ == "__main__":
    main()
