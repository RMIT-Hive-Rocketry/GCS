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


startTime = None  # init in start

# Windows Integration
if platform.system() == "Windows":
    import ctypes
    from ctypes import wintypes

    class FILETIME(ctypes.Structure):
        _fields_ = [
            ("dwLowDateTime", ctypes.c_uint32),
            ("dwHighDateTime", ctypes.c_uint32),
        ]

    class MEMORYSTATUSEX(ctypes.Structure):
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

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
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

    class proc_taskinfo(ctypes.Structure):
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

    class host_cpu_load_info_data_t(ctypes.Structure):
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
    userTime: float
    kernelTime: float
    idleTime: float
    otherTime: float  # Includes involuntary waits IRQ, etc

    usedTime: float
    usedTimeDelta: float
    cpuUsagePercent: float

    vmRss: int  # total system ram usage
    totalMem: int  # total system ram cap


@dataclass
class ProcessSystemData:
    pid: int
    name: str

    vmRss: int  # Ram Usage For The Process (kB)
    cpuUtilPercent: float
    memUtilPercent: float

    userTime: float  # Time in Jiffies / ticks in user mode
    kernelTime: float  # Time in Jiffies / ticks in kernel mode
    cpuUsageTime: float

    deltaUserTime: float  # Time in Jiffies / ticks in user mode
    deltaKernelTime: float  # Time in Jiffies / ticks in kernel mode
    deltaCpuUsageTime: float


def filetime_to_int(ft):
    return (ft.dwHighDateTime << 32) + ft.dwLowDateTime


# Extract from the proc Directory the details needed
def get_process_status_linux(pid):
    processData = ProcessSystemData(pid, "", 0, 0, 0, 0, 0, 0, 0, 0, 0)
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    processData.vmRss = int(line.split()[1])

        with open(f"/proc/{pid}/stat") as f:
            stat_cont = f.read().split()

            processData.userTime = int(stat_cont[13])  # Index within the files
            processData.kernelTime = int(stat_cont[14])
            processData.cpuUsageTime = (
                processData.userTime + processData.kernelTime
            )

        return processData

    except FileNotFoundError:
        slogger.error(f"couldn't Access {pid}")
        return None
    except Exception as e:
        slogger.error(f"Process Logging Failed to execute {e}")
        return None


# Extract from the proc Directory the details needed meminfo
def get_global_status_linux():
    sysInfo = GlobalSystemInfo(0, 0, 0, 0, 0, 0, 0, 0, 0)
    try:
        with open("/proc/stat") as f:
            for line in f:
                if line.startswith("cpu"):
                    systemList = line.split()
                    sysInfo.userTime = int(systemList[1]) + int(
                        systemList[2]
                    )  # User Global Time + User Nice Time
                    sysInfo.kernelTime = int(systemList[3])
                    sysInfo.idleTime = int(systemList[4]) + int(systemList[5])
                    sysInfo.otherTime = (
                        int(systemList[6])
                        + int(systemList[7])
                        + int(systemList[8])
                        + int(systemList[9])
                        + int(systemList[10])
                    )  # irq, softirq, steal, guest, guest_niced

                    sysInfo.usedTime = (
                        sysInfo.userTime
                        + sysInfo.kernelTime
                        + sysInfo.otherTime
                    )
                    break

        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    sysInfo.totalMem = int(line.split()[1])

                if line.startswith("MemAvailable"):
                    sysInfo.vmRss = sysInfo.totalMem - int(
                        line.split()[1]
                    )  # Used Memory equals the total memory - available to get most accurate

    except FileNotFoundError:
        slogger.error("Process Not Found")
        return sysInfo
    except Exception as e:
        slogger.error(f"Process Logging Failed to execute {e}")
        return sysInfo

    return sysInfo


# Extract from the proc Directory the details needed
def get_process_status_windows(pid):

    psapi = ctypes.WinDLL("psapi.dll")
    kernel32 = ctypes.WinDLL("kernel32.dll")

    processData = ProcessSystemData(pid, "", 0, 0, 0, 0, 0, 0, 0)

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    # PROCESS_VM_READ = 0x0010 Might Need In future

    # Get process of kernel info with perms and for a specific PID
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)

    if not handle:
        slogger.error("Invalid Hook")
        return None

    creation = FILETIME()
    exit = FILETIME()
    kernel = FILETIME()
    user = FILETIME()

    kernel32.GetProcessTimes(
        handle,
        ctypes.byref(creation),
        ctypes.byref(exit),
        ctypes.byref(kernel),
        ctypes.byref(user),
    )

    processData.userTime = filetime_to_int(user)
    processData.kernelTime = filetime_to_int(kernel)
    processData.cpuUsageTime = processData.userTime + processData.kernelTime

    # Memory Segment

    if not handle:
        slogger.error("Could not open process")
        return None

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)

    psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)

    kernel32.CloseHandle(handle)
    processData.vmRss = counters.WorkingSetSize

    return processData


def get_global_status_windows():
    sysInfo = GlobalSystemInfo(0, 0, 0, 0, 0, 0)
    kernel32 = ctypes.WinDLL("kernel32.dll")
    idle = FILETIME()
    kernel = FILETIME()
    user = FILETIME()

    kernel32.GetSystemTimes(
        ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
    )

    # Convert Propritary Windows file time to seconds
    sysInfo.idleTime = filetime_to_int(idle)
    sysInfo.kernelTime = filetime_to_int(kernel)
    sysInfo.userTime = filetime_to_int(user)
    sysInfo.usedTime = sysInfo.userTime + sysInfo.kernelTime

    x = MEMORYSTATUSEX()
    x.dwLength = ctypes.sizeof(MEMORYSTATUSEX)

    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(x))

    sysInfo.totalMem = x.ullTotalPhys
    sysInfo.vmRss = x.ullTotalPhys - x.ullAvailPhys

    return sysInfo


# Extract from the proc Directory the details needed
def get_process_status_mac(pid):
    processData = ProcessSystemData(pid, "", 0, 0, 0, 0, 0, 0, 0, 0, 0)

    info = proc_taskinfo()

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

    processData.userTime = int(user_time)
    processData.kernelTime = int(system_time)
    processData.vmRss = int(rss) / 1000  # Bytes to KB
    processData.cpuUsageTime = int(processData.userTime) + int(
        processData.kernelTime
    )
    return processData


def get_global_status_mac():
    sysInfo = GlobalSystemInfo(0, 0, 0, 0, 0, 0, 0, 0, 0)

    cpu_info = host_cpu_load_info_data_t()

    # Calculates the expected size of the struct for the kernel to fill
    count = ctypes.c_uint(ctypes.sizeof(cpu_info) // ctypes.sizeof(c_uint))

    CLK_TCK = os.sysconf("SC_CLK_TCK")  # Get Current Tick rate to convert to ns

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
    sysInfo.idleTime = idle * (1e9 / CLK_TCK)
    sysInfo.kernelTime = system * (1e9 / CLK_TCK)
    sysInfo.userTime = user * (1e9 / CLK_TCK)
    sysInfo.usedTime = sysInfo.userTime + sysInfo.kernelTime

    ### Memory

    # this script creates a subprocess with the command vm_stat and parses the data to get what is needed

    memoryData = subprocess.check_output(["vm_stat"]).decode()

    lines = memoryData.split("\n")
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

    sysInfo.totalMem = free + inactive + active + wired
    sysInfo.vmRss = active + wired

    return sysInfo


def get_process_status(pid):

    if platform.system() == "Windows":
        return get_process_status_windows(pid)
    elif platform.system() == "Linux":
        return get_process_status_linux(pid)
    elif platform.system() == "Darwin":
        return get_process_status_mac(pid)


def get_global_status():
    if platform.system() == "Windows":
        return get_global_status_windows()
    elif platform.system() == "Linux":
        return get_global_status_linux()
    elif platform.system() == "Darwin":
        return get_global_status_mac()


def main():

    # Get Arguments and Parse
    SERVICE_LIST = sys.argv[sys.argv.index("--running_services") + 1]

    global startTime
    startTime = sys.argv[sys.argv.index("--startTime") + 1]

    if SERVICE_LIST is None:
        slogger.error(
            "Please Enter a valid argument e.g. --running_services [(pid1,name1), (pid2,name2)]"
        )
        return

    if startTime is None:
        slogger.error(
            "Please Enter a valid argument e.g. --startTime from time.perf_counter()"
        )
        return

    try:
        processesDataList = ast.literal_eval(SERVICE_LIST)
    except Exception:
        slogger.error(
            "running_services argument invalid e.g. --running_services [(pid1,name1), (pid2,name2)]"
        )
        return

    previousSysData = get_global_status()
    ourPreviousSysData = []
    for ActiveProcess in processesDataList:
        ourPreviousSysData.append(get_process_status(ActiveProcess[0]))

    # Get Config File and genurate location for the new performance logging log files
    config = get_config()
    LOG_DIR_PATH = config["performance_monitor"]["performance_log_dir"].strip()
    samplingInterval = float(
        config["performance_monitor"]["performance_sampling_interval"].strip()
    )

    # Keep Track of loops to show logs to cli
    loopCount = 0
    cliLogTheshold = int(config["performance_monitor"]["performance_cli_log_interval"].strip())


    log_filename = f"performance_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    log_file_path = os.path.join(LOG_DIR_PATH, log_filename)

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

    for i in range(len(processesDataList)):
        headers += [f"pid_{i}", f"name_{i}", f"cpu_{i}", f"mem_{i}", f"rss_{i}"]

    with open(log_file_path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)

    # Sleep To Give Initial Data time to change
    time.sleep(samplingInterval)    

    while (service_helper.time_to_stop() != True):
        loopCount += 1

        # Call function to get global system data
        systemData = get_global_status()

        # Calculate Values from the global data
        totalTime = (
            systemData.userTime
            + systemData.idleTime
            + systemData.kernelTime
            + systemData.otherTime
        )
        totalTimeDelta = totalTime - (
            previousSysData.userTime
            + previousSysData.idleTime
            + previousSysData.kernelTime
            + previousSysData.otherTime
        )
        # idleTimeDelta = systemData.idleTime - (previousSysData.idleTime) Maybe useful

        systemData.usedTimeDelta = (
            systemData.usedTime - previousSysData.usedTime
        )

        # Global Values our services resource use
        ourRamUse = 0
        ourCpuUse = 0
        ourSysData: ProcessSystemData = []

        for idx, ActiveProcess in enumerate(processesDataList):
            # Get Memory Data For Process
            ps = get_process_status(ActiveProcess[0])

            if ps is None or (
                ps.vmRss == 0
                and ps.cpuUsageTime == ourPreviousSysData[idx].cpuUsageTime
            ):
                slogger.warning(
                    f"Service {ActiveProcess[1]} Cannot Be Accessed No Longer Logging"
                )
                processesDataList.pop(idx)
                continue

            # Countinus Addition of ram usage percent across system
            ourRamUse += +ps.vmRss

            ps.memUtilPercent = ps.vmRss / systemData.totalMem

            # Assign Individual deltas to the processes
            ps.deltaKernelTime = (
                ps.kernelTime - ourPreviousSysData[idx].kernelTime
            )
            ps.deltaUserTime = ps.userTime - ourPreviousSysData[idx].userTime

            ps.deltaCpuUsageTime = (
                ps.cpuUsageTime - ourPreviousSysData[idx].cpuUsageTime
            )

            # Total Current CpuUse cycles added across all monitored processes
            ourCpuUse += ps.deltaCpuUsageTime

            # map indiviudal utilisation to each processes
            if totalTimeDelta != 0:
                ps.cpuUtilPercent = (
                    ps.deltaCpuUsageTime / totalTimeDelta
                ) * 100
            else:
                ps.cpuUtilPercent = 0

            # Add pid and name into the process info that was passed initially from args
            ps.pid = ActiveProcess[0]
            ps.name = ActiveProcess[1]

            ourSysData.append(ps)

        if totalTimeDelta != 0:
            ourCpuUsePercent = (ourCpuUse / totalTimeDelta) * 100
            systemData.cpuUsagePercent = (
                systemData.usedTimeDelta / totalTimeDelta
            ) * 100
        else:
            ourCpuUsePercent = 0
            systemData.cpuUsagePercent = 0

        ourRamUsePercent = (ourRamUse / systemData.totalMem) * 100
        totalRamUsePercent = (systemData.vmRss / systemData.totalMem) * 100

        # Gen dynamic rows for each service
        row = [
            round(time.time(), 3),
            str(round(time.perf_counter() - float(startTime), 3)),
            round(totalRamUsePercent, 3),
            round(ourRamUsePercent, 7),
            round(systemData.cpuUsagePercent, 7),
            round(ourCpuUsePercent, 7),
        ]

        # Generate dynamic string of processes and details to append onto log
        for osd in ourSysData:
            row.extend(
                [
                    osd.pid,
                    osd.name,
                    round(osd.cpuUtilPercent, 7),
                    round(osd.memUtilPercent, 5),
                    round(osd.vmRss, 2),
                ]
            )

        with open(log_file_path, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(row)

        # This is in seconds as one loop executes every second
        if (loopCount >= cliLogTheshold):
            slogger.debug(f"System CPU Util: {round(systemData.cpuUsagePercent,2)}% Ram Util: {round(totalRamUsePercent,2)}%")
            slogger.debug(f"Program CPU Util: {round(ourCpuUsePercent,2)}% Ram Util: {round(ourRamUsePercent,2)}%")
            loopCount = 0

        # Update Old Values with current ones
        previousSysData = systemData

        ourPreviousSysData.clear()
        for ActiveProcess in processesDataList:
            ourPreviousSysData.append(get_process_status(ActiveProcess[0]))

        # Wait For Next sampling Interval
        time.sleep(samplingInterval)


if __name__ == "__main__":
    main()
