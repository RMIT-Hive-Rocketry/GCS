import os
import backend.includes_python.process_logging as slogger
import cli.proccess as process
import time
import sys
import platform
from dataclasses import dataclass
from config.config import get_config
import ast
import csv
import backend.includes_python.service_helper as service_helper



startTime = None # init in start

# Windows Intergration
if(platform.system() == "Windows"):
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

elif (platform.system() == "Darwin"):
    slogger.error("Performance Monitor Is not Supported On Mac please use Linux Or Windows !")
    sys.exit("Invalid OS")
elif (platform.system() == "Linux"):
    pass
else:
    slogger.error("Performance Monitor Is not Supported On this OS please use Linux Or Windows !")
    sys.exit("Invalid OS")

# Got most of declarations from https://docs.kernel.org/filesystems/proc.html

@dataclass
class GlobalSystemInfo:
    userTime: float
    kernelTime: float
    idleTime: float
    otherTime: float # Includes involuntary waits IRQ, etc

    usedTime: float
    usedTimeDelta: float
    cpuUsagePercent: float

    vmRss: int # total system ram useage
    totalMem: int # total system ram cap


@dataclass
class ProcessSystemData:
    pid: int
    name: str

    vmRss: int # Ram Useage For The Process (kB)
    cpuUtilPercent: float
    memUtilPercent: float


    userTime: float # Time in Jiffies / ticks in user mode
    kernelTime: float # Time in Jiffies / ticks in kernel mode
    cpuUsageTime: float

    deltaUserTime: float # Time in Jiffies / ticks in user mode
    deltaKernelTime: float # Time in Jiffies / ticks in kernel mode
    deltaCpuUsageTime: float


def filetime_to_int(ft):
    return (ft.dwHighDateTime << 32) + ft.dwLowDateTime

# Extract from the proc Directory the details needed
def get_process_status_linux(pid):
    processData = ProcessSystemData(pid, "", 0,0,0,0,0,0,0,0,0)
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    processData.vmRss = int(line.split()[1])

        with open(f"/proc/{pid}/stat") as f:
            stat_cont = f.read().split()

            processData.userTime = int(stat_cont[13]) # Index within the files
            processData.kernelTime = int(stat_cont[14])
            processData.cpuUsageTime = processData.userTime + processData.kernelTime

        return processData

    except FileNotFoundError:
        return None
    
# Extract from the proc Directory the details needed meminfo 
def get_global_status_linux():
    sysInfo = GlobalSystemInfo(0,0,0,0,0,0,0,0,0)
    try:
        with open(f"/proc/stat") as f:
            for line in f:
                if line.startswith("cpu"):
                    systemList = line.split()
                    sysInfo.userTime = int(systemList[1] + systemList[2]) # User Global Time + User Nice Time
                    sysInfo.kernelTime = int(systemList[3])
                    sysInfo.idleTime = int(systemList[4] + systemList[5])
                    sysInfo.otherTime = int(systemList[6] + systemList[7] + systemList[8] + systemList[9] + systemList[10]) # irq, softirq, steal, guest, guest_niced

                    sysInfo.usedTime = sysInfo.userTime + sysInfo.kernelTime + sysInfo.otherTime
                    break
        
        with open(f"/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    sysInfo.totalMem = int(line.split()[1])

                if line.startswith("MemAvailable"):
                    sysInfo.vmRss = sysInfo.totalMem - int(line.split()[1]) # Used Memory equals the total memory - avaliable to get most acurate
    
    except FileNotFoundError:
        return None
    except Exception as e:
        slogger.error("Process Logging Failed to execute {e}")
        return None



    return sysInfo


# Extract from the proc Directory the details needed
def get_process_status_windows(pid):

    psapi = ctypes.WinDLL("psapi.dll")
    kernel32 = ctypes.WinDLL("kernel32.dll")

    processData = ProcessSystemData(pid, "", 0,0,0,0,0,0,0)

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_VM_READ = 0x0010

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)

    if not handle:
        print("Invalid Hook")
        return processData

    creation = FILETIME()
    exit = FILETIME()
    kernel = FILETIME()
    user = FILETIME()

    kernel32.GetProcessTimes(
        handle,
        ctypes.byref(creation),
        ctypes.byref(exit),
        ctypes.byref(kernel),
        ctypes.byref(user)
    )

    print(user, kernel, exit, creation)

    processData.userTime =  filetime_to_int(user)
    processData.kernelTime =  filetime_to_int(kernel)
    processData.cpuUsageTime = processData.userTime + processData.kernelTime

    # Memory Segment

    if not handle:
        raise OSError("Could not open process")

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)

    psapi.GetProcessMemoryInfo(
        handle,
        ctypes.byref(counters),
        counters.cb
    )

    kernel32.CloseHandle(handle)
    processData.vmRss = counters.WorkingSetSize

    return processData
   


def get_global_status_windows():
    sysinfo = GlobalSystemInfo(0,0,0,0,0,0)
    kernel32 = ctypes.WinDLL("kernel32.dll")
    idle = FILETIME()
    kernel = FILETIME()
    user = FILETIME()

    kernel32.GetSystemTimes(
        ctypes.byref(idle),
        ctypes.byref(kernel),
        ctypes.byref(user)
    )

    sysinfo.idleTime = filetime_to_int(idle)
    sysinfo.kernelTime = filetime_to_int(kernel)
    sysinfo.userTime = filetime_to_int(user)
    sysinfo.usedTime = sysinfo.userTime + sysinfo.kernelTime

    x = MEMORYSTATUSEX()
    x.dwLength = ctypes.sizeof(MEMORYSTATUSEX)

    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(x))


    sysinfo.totalMem = x.ullTotalPhys
    sysinfo.vmRss = x.ullTotalPhys - x.ullAvailPhys


    return sysinfo





def get_process_status(pid):
    
    if(platform.system() == "Windows"):
        return get_process_status_windows(pid)
    elif (platform.system() == "Linux"):
        return get_process_status_linux(pid)

def get_global_status():
    if(platform.system() == "Windows"):
        return get_global_status_windows()
    elif (platform.system() == "Linux"):
        return get_global_status_linux()
    

def main():
    
    # Get Arguments and Parse
    SERVICE_LIST = sys.argv[sys.argv.index("--running_services") + 1]

    global startTime
    startTime = sys.argv[sys.argv.index("--startTime") + 1]
    
    processesDataList = ast.literal_eval(SERVICE_LIST)


    previousSysData = get_global_status()
    ourPreviousSysData = []
    for ActiveProcess in processesDataList:
        ourPreviousSysData.append(get_process_status(ActiveProcess[0]))
    

    # Get Config File and genurate location for the new performance logging log files
    config = get_config()
    LOG_DIR_PATH = config["performance_monitor"]["performance_log_dir"].strip()
    samplingInterval = float(config["performance_monitor"]["performance_sampling_interval"].strip())

    log_filename = f"performance_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    log_file_path = os.path.join(LOG_DIR_PATH, log_filename)

    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)



    # Prepare Log Header 
    headers = [
        "timestamp",
        "total_ram_percent",
        "our_ram_percent",
        "total_cpu_percent",
        "our_cpu_percent"
    ]

    for i in range(len(processesDataList)):
        headers += [
            f"pid_{i}",
            f"name_{i}",
            f"cpu_{i}",
            f"mem_{i}",
            f"rss_{i}"
        ]

    with open(log_file_path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)


    # Sleep To Give Initial Data time to change
    time.sleep(samplingInterval)    

    while (service_helper.time_to_stop() != True):


        # Call function to get global system data
        systemData = get_global_status()

        # Calculate Values from the global data
        totalTime = systemData.userTime + systemData.idleTime + systemData.kernelTime + systemData.otherTime
        totalTimeDelta = totalTime - (previousSysData.userTime + previousSysData.idleTime + previousSysData.kernelTime + previousSysData.otherTime)
        idleTimeDelta = systemData.idleTime - (previousSysData.idleTime)

        systemData.usedTimeDelta = systemData.usedTime - previousSysData.usedTime


        # Global Values our services resource use
        ourRamUse = 0
        ourCpuUse = 0
        ourSysData:ProcessSystemData = []

        for idx, ActiveProcess in enumerate(processesDataList):
            # Get Memory Data For Process
            ps = get_process_status(ActiveProcess[0])

            # Countinus Addition of ram useage percent across system from psUtil
            ourRamUse += + ps.vmRss

            ps.memUtilPercent = ps.vmRss / systemData.totalMem


            # Total Current CpuUse cycles added across all monitored processes
            ourCpuUse += ps.cpuUsageTime

            # Assign Individual deltas to the processes
            ps.deltaKernelTime = ps.kernelTime - ourPreviousSysData[idx].kernelTime
            ps.deltaUserTime = ps.userTime - ourPreviousSysData[idx].userTime

            ps.deltaCpuUsageTime = ps.cpuUsageTime - ourPreviousSysData[idx].cpuUsageTime

            # map indiviudal utilsation to each processes
            if(totalTimeDelta != 0):
                ps.cpuUtilPercent = (ps.deltaCpuUsageTime / totalTimeDelta) * 100
            else:
                ps.cpuUtilPercent = 0

            # Add pid and name into the process info that was passed initially from args
            ps.pid = ActiveProcess[0] 
            ps.name = ActiveProcess[1]
 
            ourSysData.append(ps)
        

        if(totalTimeDelta != 0):
            ourCpuUsePercent = (ourCpuUse / totalTimeDelta) * 100
            systemData.cpuUsagePercent = (systemData.usedTimeDelta / totalTimeDelta) * 100
        else:
            ourCpuUsePercent = 0
            systemData.cpuUsagePercent = 0


        ourRamUsePercent = (ourRamUse / systemData.totalMem) * 100
        totalRamUsePercent = (systemData.vmRss / systemData.totalMem) * 100
        
        # Gen dynamic rows for each service
        row = [
            str(round(time.perf_counter() - float(startTime), 3)),
            round(totalRamUsePercent, 3),
            round(ourRamUsePercent, 7),
            round(systemData.cpuUsagePercent, 7),
            round(ourCpuUsePercent, 7)
        ]

        # flatten process data
        for osd in ourSysData:
            row.extend([
                osd.pid,
                osd.name,
                round(osd.cpuUtilPercent, 7),
                round(osd.memUtilPercent, 5),
                round(osd.vmRss, 2)
            ])
        
        with open(log_file_path, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(row)

        # Update Old Values with current ones
        previousSysData = systemData

        ourPreviousSysData.clear()
        for ActiveProcess in processesDataList:
            ourPreviousSysData.append(get_process_status(ActiveProcess[0]))


        # Wait For Next sampling Interval
        time.sleep(samplingInterval)


if __name__ == "__main__":
    main()