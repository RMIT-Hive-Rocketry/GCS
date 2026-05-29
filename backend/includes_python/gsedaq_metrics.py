import ast
import re

import backend.includes_python.process_logging as slogger
import config.config as config
from typing import List, Any, Dict
from dataclasses import dataclass
from functools import cache

_LABVIEW_VAL_RE = re.compile(r"<Val>\s*(.*?)\s*</Val>", re.DOTALL)

# Provides the packet structures for emulating GSE/DAQ in device_emulator.py
# The data coming from this system is meant to emaulate what you would get from the labview TCP server

GSE_SENSOR_OFFLINE_VALUE = "offline"


def _parse_ini_bool(raw: str) -> bool:
    """
    Parse [gse_sensors] *_enabled values; ignores trailing inline # or ; comments.
    Once again, another reason to move to .yaml from GCS-2026#50
    """
    if raw is None:
        return False
    v = raw.split("#", 1)[0].split(";", 1)[0].strip().lower()
    return v in ("1", "true", "yes", "on")


@dataclass
class GseDaqMetrics:
    # More information:
    # RMIT ONLY: https://rmiteduau.sharepoint.com/:x:/r/sites/RMITHIVERocketTeam/Shared%20Documents/00%202026%20Competitions/IREC%202026/3.0%20Ground%20Control/daq/DAQ%20Sensors%20for%20GL.xlsx?d=w9088d352929443bb8d0e68a94ac8a5aa&csf=1&web=1&e=7MxgVF
    temp_tank_top: float
    temp_tank_middle: float
    temp_tank_bottom: float
    temp_vent: float
    temp_pipe_n2o_gse: float
    pressure_n2o_bottle: float
    pressure_n2o_tank: float
    pressure_o2_tank: float
    weight_rocket: float

    # TODO update with actual labview pattern when ready
    # Assuming the data from labview will look like this
    # <Val>[[name,value],[name2,value2],[...],[...]]</Val>

    @staticmethod
    def build_xml_row(data: Dict[str, Any]) -> str:
        """
        Returns a complete row XML update which appears in each lavbiew update
        Note that this emulation is clean, and does not come in chunks like a typical TCP buffer will do.

        args: data: {"metric_name": value, "metric_name2": value2} — values may be floats or ``"offline"``.
        """
        # TODO update with actual labview pattern when ready
        data_list: List[List[Any]] = []
        for metric, value in data.items():
            data_list.append([metric, value])
        formatted_data = str(data_list)
        return f"<Val>{formatted_data}</Val>"

    @staticmethod
    def build_labview_row_dict(
        live_values: Dict[str, float],
        enabled_by_metric: Dict[str, bool],
    ) -> Dict[str, Any]:
        """Replace disabled metrics with ``offline``; enabled metrics keep simulated floats."""
        out: Dict[str, Any] = {}
        for name, value in live_values.items():
            if enabled_by_metric.get(name, True):
                out[name] = value
            else:
                out[name] = GSE_SENSOR_OFFLINE_VALUE
        return out

    @staticmethod
    def labview_row_bytes_to_data_dict(row: bytes) -> Dict[str, Any]:
        """Parse a `<Val>[[name, value], ...]</Val>` line (TCP/LabVIEW) into a metric dict."""
        text = row.decode("utf-8").strip()
        m = _LABVIEW_VAL_RE.search(text)
        # Note that an incomplete buffer will fail on this
        # Make sure you are sending a full XML tag each time
        # Should be fine for emulation and should be fine if labview is atomic with it's messaging
        if not m:
            # TODO update with actual labview pattern when ready
            raise ValueError("expected <Val>...</Val>")
        pairs = ast.literal_eval(m.group(1))
        return {name: val for name, val in pairs}

    @staticmethod
    @cache
    def get_gse_sensor_enabled_map() -> Dict[str, bool]:
        """Maps metric field name -> whether that sensor is enabled in ``config.ini``."""
        the_config = config.get_config()
        enabled: Dict[str, bool] = {}
        for config_name in the_config["gse_sensors"]:
            if config_name.endswith("_enabled"):
                metric_name = config_name.replace("_enabled", "")
                raw = the_config["gse_sensors"][config_name]
                enabled[metric_name] = _parse_ini_bool(raw)
        return enabled
