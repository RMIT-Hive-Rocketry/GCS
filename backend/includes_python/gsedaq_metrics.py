import backend.includes_python.process_logging as slogger
import config.config as config
from typing import List, Any
from dataclasses import dataclass

# Provides the packet structures for emulating GSE/DAQ in device_emulator.py
# The data coming from this system is meant to emaulate what you would get from the labview TCP server


def get_enabled_features():
    config = config.get_config()
    metrics = {}
    for config_name in config["gse_sensors"]:
        if config_name.endswith("_enabled"):
            metric_name = config_name.relpace("_enabled", "")
            metric_status = config["gse_sensors"][config_name]
            metrics[metric_name] = {"status": metric_status}
    return metrics


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

    # Assuming the data from labview will look like this
    # <Val>[[name,value],[name2,value2],[...],[...]]</Val>

    @staticmethod
    def build_xml_row(data: dict) -> str:
        """
        Returns a complete row XML update which appears in each lavbiew update
        Note that this emulation is clean, and does not come in chunks like a typical TCP buffer will do.

        args: data: {"metric_name": value, "metric_name2": value2}
        """
        data_list: List[List[Any]] = []
        for metric, value in data.items():
            data_list.append([metric, value])
        formatted_data = str(data_list)
        return f"<Val>{formatted_data}</Val>"
