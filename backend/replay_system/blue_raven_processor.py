import csv
import os
import bisect
import math
from backend.replay_system.packet import PacketType
from backend.replay_system.packet import Packet
import backend.includes_python.process_logging as slogger


def process_blue_raven(replay_name: str) -> list[Packet]:
    packets = []

    filepath = os.path.join(get_blue_raven_path(), replay_name)

    hr_filename = ""
    lr_filename = ""

    try:
        for filename in os.listdir(filepath):
            if "hr" in filename.lower():
                hr_filename = filename
            if "lr" in filename.lower():
                lr_filename = filename

        if hr_filename == "" or lr_filename == "":
            slogger.error(f"Missing file: {filepath}")
            raise

        hr_filepath = os.path.join(filepath, hr_filename)
        slogger.debug(f"{hr_filepath}")
        hr_file = open(hr_filepath, encoding="utf-8-sig")
        hr_reader = csv.DictReader(hr_file)
        hr_rows = list(hr_reader)

        lr_filepath = os.path.join(filepath, lr_filename)
        lr_file = open(lr_filepath, encoding="utf-8-sig")
        lr_reader = csv.DictReader(lr_file)
        lr_rows = list(lr_reader)

        rows = _merge_rows(hr_rows, lr_rows)

        first_timestamp_offset = min(
            [float(row["Flight_Time_(s)"]) for row in rows]
        )
        for row in rows:
            row_packets = _get_packets_from_row(row, first_timestamp_offset)
            packets.extend(row_packets)

    except FileNotFoundError:
        slogger.error(f"Missing file: {filepath}")
    except Exception as e:
        slogger.error(f"Error parsing Blue Raven data: {e}")

    return packets


def _get_closest_lr_row_index(hr_row_time: float, lr_times: list[float]) -> int:
    index = bisect.bisect_left(lr_times, hr_row_time)
    if index >= len(lr_times):
        index = len(lr_times) - 1
    return index


def _merge_rows(hr_rows: list[dict], lr_rows: list[dict]) -> list[dict]:
    lr_times = [float(row["Flight_Time_(s)"]) for row in lr_rows]
    merged_rows = []
    for hr_row in hr_rows:
        hr_row_time = float(hr_row["Flight_Time_(s)"])

        closest_lr_row_index = _get_closest_lr_row_index(hr_row_time, lr_times)
        closest_lr_row = lr_rows[closest_lr_row_index]
        merged_row = dict(hr_row)
        merged_row.update(closest_lr_row)
        merged_rows.append(merged_row)

    return merged_rows


def get_blue_raven_path():
    base_path = os.path.join("backend", "replay_system", "blue_raven")
    return base_path


def _get_data_1(row: dict, corrected_timestamp: float) -> dict:

    velocity = math.sqrt(
        (float(row["Velocity_Up"]) * 0.3048) ** 2
        + (float(row["Velocity_DR"]) * 0.3048) ** 2
        + (float(row["Velocity_CR"]) * 0.3048) ** 2
    )
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
        "altitude": float(row["Baro_Altitude_ASL_(feet)"]) * 0.3048,
        "velocity": velocity,
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


def _get_packets_from_row(
    row: dict, first_timestamp_offset: float
) -> list[Packet]:
    corrected_timestamp = _compute_correct_timestamp(
        float(row["Flight_Time_(s)"]), first_timestamp_offset
    )
    packet_1 = Packet(
        corrected_timestamp,
        PacketType.AV_TO_GCS_DATA_1,
        _get_data_1(row, corrected_timestamp),
    )
    packet_2 = Packet(
        corrected_timestamp,
        PacketType.AV_TO_GCS_DATA_2,
        _get_data_2(row, corrected_timestamp),
    )
    return [packet_1, packet_2]
