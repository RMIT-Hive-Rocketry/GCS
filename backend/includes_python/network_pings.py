import asyncio
from collections import deque
import backend.includes_python.process_logging as slogger


try:
    import ping3
except ModuleNotFoundError:
    ping3 = None


# Edit this to whatever you want to just test things
TEST_NETWORK_DEVICE_MANIFEST = {
    "Google": "google.com",
    "My Phone (LAN)": "192.168.0.49"
}

HIVE_NETWORK_DEVICE_MANIFEST = {
    "TP-Link Router": "192.168.0.1",
    "GC-1": "192.168.0.3",
    "GC-2": "192.168.0.2",
    "Launchpad Camera": "192.168.0.60",
    "LabJack": "192.168.0.100",
    "QuantumX DAQ": "192.168.0.132",
    "DAQ 4 Channel": "192.168.0.133",
    "Vulcan ESP32": "192.168.0.150",
    "WiFi Bridge @ GSE": "192.168.0.253",
    "WiFi Bridge @ GCS": "192.168.0.254",
}

# Change it here based on test or prod mode.
# This should be auto based on the environment mode but i cbf right now.
# It needs fixes outlines in GCS-2026#50
default_manifest = TEST_NETWORK_DEVICE_MANIFEST

# Store information about each device and it's packet loss here.
# Ring buffer of last 30 pings or so. Based on amount, not time.
# Start with all sucesses
ping_sucess_buffer_size = 30
ping_sucess_cache = {name: deque([True]*ping_sucess_buffer_size,
                                 maxlen=ping_sucess_buffer_size)
                     for name in default_manifest.keys()}


async def ping_address(device: str, address: str) -> tuple[str, float, float]:
    """returns (device, ping_ms, packet_loss%)"""
    if ping3 is None:
        latency_ms = None
    else:
        try:
            latency_ms = await asyncio.to_thread(
                ping3.ping,
                address,
                unit="ms",
                timeout=1.0,
            )
        except Exception:
            latency_ms = None

    # Failed
    if latency_ms in (None, False):
        ping_sucess_cache[device].append(False)
        latency_ms = -1
    else:
        ping_sucess_cache[device].append(True)

    return device, float(latency_ms), 1-sum(ping_sucess_cache[device])/ping_sucess_buffer_size


async def ping_manifest() -> dict[str, float | None]:
    ping_tasks = [ping_address(d, a) for d, a in default_manifest.items()]
    ping_results = await asyncio.gather(*ping_tasks)

    return {dev: {"ping": ping, "packet_loss": pl} for dev, ping, pl in ping_results}
