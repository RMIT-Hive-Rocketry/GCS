import csv
import os
from backend.replay_system.packet import PacketType
from backend.replay_system.packet import Packet
import backend.includes_python.process_logging as slogger


def process_blue_raven(filepath: str) -> list[Packet]:
    packets = []

    try:
        with open(filepath, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            first_timestamp_offset = min([float(row["Flight_Time_(s)"]) for row in rows])
            for row in rows:
                row_packets = _get_packets_from_row(row, first_timestamp_offset)
                packets.extend(row_packets)

    except FileNotFoundError:
        slogger.error(f"Warning Missing File: {filepath}")
    return packets

def get_blue_raven_path():
    base_path = os.path.join("backend", "replay_system", "blue_raven")
    return base_path

def _get_data_1(row: dict, corrected_timestamp: float) -> dict:
    return {
        "timestamp_ms": corrected_timestamp,
        "rssi": 0,
        "snr": 0,
        "FlightState": 0,
        "dual_board_connectivity_state_flag": False,
        "recovery_checks_complete_and_flight_ready": False,
        "GPS_fix_flag": False,
        "payload_connection_flag": False,
        "camera_controller_connection_flag": False,
        "accel_low_x": float(row["Accel_X"]),
        "accel_low_y": float(row["Accel_Y"]),
        "accel_low_z": float(row["Accel_Z"]),
        "accel_high_x": 0,
        "accel_high_y": 0,
        "accel_high_z": 0,
        "gyro_x": float(row["Gyro_X"]),
        "gyro_y": float(row["Gyro_Y"]),
        "gyro_z": float(row["Gyro_Z"]),
        "altitude": 0.0,
        "velocity": 0.0,
        "apogee_primary_test_complete": False,
        "apogee_secondary_test_complete": False,
        "apogee_primary_test_results": False,
        "apogee_secondary_test_results": False,
        "main_primary_test_complete": False,
        "main_secondary_test_complete": False,
        "main_primary_test_results": False,
        "main_secondary_test_results": False,
        "broadcast_flag": False,
    }

def _get_data_2(row: dict, corrected_timestamp: float) -> dict:
    return {
            "timestamp_ms": corrected_timestamp,
            "rssi": 0,
            "snr": 0,
            "FlightState": 0,
            "dual_board_connectivity_state_flag": False,
            "recovery_checks_complete_and_flight_ready": False,
            "GPS_fix_flag": False,
            "payload_connection_flag": False,
            "camera_controller_connection_flag": False,
            "GPS_latitude": 0,
            "GPS_longitude": 0,
            "qw": float(row["Quat_1"]),
            "qx": float(row["Quat_2"]),
            "qy": float(row["Quat_3"]),
            "qz": float(row["Quat_4"]),
    }

def _compute_correct_timestamp(timestamp, first_timestamp_offset):
    return (timestamp - first_timestamp_offset) * 1000

def _get_packets_from_row(row: dict, first_timestamp_offset: float) -> list[Packet]:
    corrected_timestamp = _compute_correct_timestamp(float(row["Flight_Time_(s)"]), first_timestamp_offset)
    packet_1 = Packet(
        corrected_timestamp,
        PacketType.AV_TO_GCS_DATA_1,
        _get_data_1(row, corrected_timestamp)
    )
    packet_2 = Packet(
        corrected_timestamp,
        PacketType.AV_TO_GCS_DATA_2,
        _get_data_2(row, corrected_timestamp)
    )
    return [packet_1, packet_2]

