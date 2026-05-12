from __future__ import absolute_import
from abc import ABC, abstractmethod
import config.config as config
from typing import Optional, List, Tuple
from dataclasses import asdict
import sys
import socket
import random
import struct
from backend.includes_python import metric
import os
import time
import backend.includes_python.process_logging as slogger  # slog deez nuts
import backend.includes_python.service_helper as service_helper
from cli.start_middleware import InterfaceType, get_interface_type
import enum
import math
from backend.includes_python.metric import Metric
from backend.includes_python.gsedaq_metrics import GseDaqMetrics
import threading

# This file can be imported or rain as an emulation service if __main__
# This file is for lower level emulation. Hence some things are passed bitwise
# If you want higher level emulation, please talk to @mcloughlan and I will
# make a higher level emulation library so it's not repeated for each person


class MockPacket(ABC):
    # Name of the fake device socat has made
    _FAKE_DEVICE_NAME: Optional[str] = None
    _INITIALISED: bool = (
        False  # Flag to check if the settings have been initialized
    )
    _write_lock = threading.Lock()

    TIME_INBETWEEN_PACKETS = 0.01

    class _SourceDevice(enum.Enum):
        AV = enum.auto()
        GSE = enum.auto()
        GCS = enum.auto()

    @classmethod
    def initialize_settings(
        cls,
        EMULATION_CONFIG: dict,
        FAKE_DEVICE_NAME: str = None,
        INTERFACE_TYPE: InterfaceType = InterfaceType.TEST,
    ):
        """Initialise settings for the MockPacket object

        Args:
            EMULATION_CONFIG (dict): Config settings from an .ini file
        """

        if cls._INITIALISED:
            raise ValueError("Settings have already been initialized.")
        # Might need this config code later, if it's like march or later it can go
        # if "emulator_device_name" not in EMULATION_CONFIG.keys():
        #     raise KeyError("Missing 'emulator_device_name' in configuration.")

        # Set static class values
        cls._FAKE_DEVICE_NAME = FAKE_DEVICE_NAME
        cls._INITIALISED = True
        MockPacket._INTERFACE_TYPE = INTERFACE_TYPE
        MockPacket._NOISE_COEFFICIENT = float(
            EMULATION_CONFIG["noise_coefficient"]
        )
        MockPacket._PACKET_LOSS = float(
            EMULATION_CONFIG["packet_loss"]
        )  # [0-1]

    def __init__(self):
        if not self._INITIALISED:
            raise RuntimeError(
                "Cannot create instances of MockPacket or its subclasses before initializing class settings."
            )
        self.ID: Optional[int] = None  # Packet ID
        # High level payload builder
        self.payload_after_id_and_meta: Optional[List[bytes]] = None
        self.ORIGIN_DEVICE: Optional[MockPacket._SourceDevice] = None

    def write_payload(self):
        """Writes payload of bytes to device"""

        if self._FAKE_DEVICE_NAME is None:
            raise ValueError("Cannot write to device. Device name not set.")
        try:
            payload_bytes = self.get_payload_bytes()
            with MockPacket._write_lock:
                with open(self._FAKE_DEVICE_NAME, "wb") as device:
                    device.write(payload_bytes)
        except Exception as e:
            slogger.error(
                f"Failed to write bytes to {self._FAKE_DEVICE_NAME}: {e}"
            )
            raise

    def get_payload_bytes(self, EXTERNAL=False) -> bytes:
        """Concatenates the ID and payload fragments into a single bytes object."""

        def _format_test_payload() -> bytes:
            output_bytes = bytearray()
            output_bytes.extend(metric.Metric._int_to_byte_unsigned(self.ID))
            if not EXTERNAL:
                output_bytes.extend(metric.Metric._float32_to_bytes(self.RSSI))
                output_bytes.extend(metric.Metric._float32_to_bytes(self.SNR))
            for fragment in self.payload_after_id_and_meta:
                output_bytes.extend(fragment)
            return output_bytes

        def _format_test_uart_payload() -> bytes:
            # Responses looks like this
            # ...
            # +TEST: LEN:32, RSSI:-46, SNR:10
            # +TEST: RX
            # "0400FFEA0838001FFFDA0400FFC1FFEB0007FFA73C6DAABE0000000000000000"
            # +TEST: LEN:32, RSSI:-45, SNR:10
            # +TEST: RX
            # "0400001908490042FFCD03F7FFCFFFC0002DFFE93C6DAABE0000000000000000"
            # ...
            CRLF = "\r\n"
            header = (
                f"+TEST: LEN:{len(self.payload_after_id_and_meta)+1}, RSSI:{int(round(self.RSSI))}, SNR:{int(round(self.SNR))}"
                + CRLF
            )
            header_suffix = "+TEST: RX" + "\n"
            data_payload_bytes = bytearray()
            data_payload_bytes.extend(
                metric.Metric._int_to_byte_unsigned(self.ID)
            )
            for fragment in self.payload_after_id_and_meta:
                data_payload_bytes.extend(fragment)
            data_payload_hex_line = f'"{data_payload_bytes.hex()}"' + CRLF
            output_string = header + header_suffix + data_payload_hex_line
            return output_string.encode("ascii")

        match MockPacket._INTERFACE_TYPE:
            case InterfaceType.TEST:
                return _format_test_payload()
            case InterfaceType.TEST_UART_E5:
                return _format_test_uart_payload()


class GCStoGSEStateCMD(MockPacket):
    def __init__(
        self,
        RSSI: float = 0.0,
        SNR: float = 69,
        MANUAL_PURGE: bool = False,
        O2_FILL_ACTIVATE: bool = True,
        SELECTOR_SWITCH_NEUTRAL_POSITION: bool = False,
        N2O_FILL_ACTIVATE: bool = False,
        IGNITION_FIRE: bool = False,
        IGNITION_SELECTED: bool = False,
        GAS_FILL_SELECTED: bool = False,
        SYSTEM_ACTIVATE: bool = False,
    ):
        super().__init__()
        self.ID = 0x02
        self.RSSI = RSSI
        self.SNR = SNR
        self.ORIGIN_DEVICE = MockPacket._SourceDevice.GCS
        self.payload_after_id_and_meta = [
            metric.Metric.StateSetFlags2p1(
                MANUAL_PURGE,
                O2_FILL_ACTIVATE,
                SELECTOR_SWITCH_NEUTRAL_POSITION,
                N2O_FILL_ACTIVATE,
                IGNITION_FIRE,
                IGNITION_SELECTED,
                GAS_FILL_SELECTED,
                SYSTEM_ACTIVATE,
            ),
            metric.Metric.StateSetFlagINVERTEDs2p2(
                MANUAL_PURGE,
                O2_FILL_ACTIVATE,
                SELECTOR_SWITCH_NEUTRAL_POSITION,
                N2O_FILL_ACTIVATE,
                IGNITION_FIRE,
                IGNITION_SELECTED,
                GAS_FILL_SELECTED,
                SYSTEM_ACTIVATE,
            ),
            metric.Metric.dummyByte(),
        ]


class GCStoAVStateCMD(MockPacket):
    def __init__(
        self,
        RSSI: float = 0.0,
        SNR: float = 69,
        MAIN_SECONDARY_TEST: bool = False,
        MAIN_PRIMARY_TEST: bool = True,
        APOGEE_SECONDARY_TEST: bool = False,
        APROGEE_PRIMARY_TEST: bool = False,
        BEGIN_BROADCAST: bool = False,
    ):
        super().__init__()
        self.ID = 0x01
        self.RSSI = RSSI
        self.SNR = SNR
        self.ORIGIN_DEVICE = MockPacket._SourceDevice.GCS
        self.payload_after_id_and_meta = [
            metric.Metric.continuityCheckCMDFlags(
                MAIN_SECONDARY_TEST,
                MAIN_PRIMARY_TEST,
                APOGEE_SECONDARY_TEST,
                APROGEE_PRIMARY_TEST,
            ),
            metric.Metric.continuityCheckCMDFlagsINVERTED(
                MAIN_SECONDARY_TEST,
                MAIN_PRIMARY_TEST,
                APOGEE_SECONDARY_TEST,
                APROGEE_PRIMARY_TEST,
            ),
            metric.Metric.BroadcastBeginCMDFlags(BEGIN_BROADCAST),
        ]


class GCStoGSEManualControl(GCStoGSEStateCMD):
    """Same command as GCStoGSEStateCMD but with different ID to indicate manual control"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ID = 0x09


class AVtoGCSData1(MockPacket):
    def __init__(
        self,
        RSSI: float = 0.0,
        SNR: float = 61,
        FLIGHT_STATE_: int = 0,
        DUAL_BOARD_CONNECTIVITY_STATE_FLAG=False,
        RECOVERY_CHECK_COMPLETE_AND_FLIGHT_READY=False,
        GPS_FIX_FLAG=False,
        PAYLOAD_CONNECTION_FLAG=True,
        CAMERA_CONTROLLER_CONNECTION=True,
        ACCEL_LOW_X=2048 * 1,
        ACCEL_LOW_Y=2048 * 2,
        ACCEL_LOW_Z=-2048 * 3,
        ACCEL_HIGH_X=-1024 * 1,
        ACCEL_HIGH_Y=-1024 * 2,
        ACCEL_HIGH_Z=1024 * 3,
        GYRO_X=int(1 / 0.00875),
        GYRO_Y=int(2 / 0.00875),
        GYRO_Z=int(3 / 0.00875),
        ALTITUDE=1234,
        VELOCITY=1234,
        APOGEE_PRIMARY_TEST_COMPETE=True,
        APOGEE_SECONDARY_TEST_COMPETE=False,
        APOGEE_PRIMARY_TEST_RESULTS=False,
        APOGEE_SECONDARY_TEST_RESULTS=False,
        MAIN_PRIMARY_TEST_COMPETE=True,
        MAIN_SECONDARY_TEST_COMPETE=False,
        MAIN_PRIMARY_TEST_RESULTS=False,
        MAIN_SECONDARY_TEST_RESULTS=False,
        MOVE_TO_BROADCAST=False,
    ):
        super().__init__()
        self.ID = 0x03
        self.RSSI = RSSI
        self.SNR = SNR
        self.ORIGIN_DEVICE = MockPacket._SourceDevice.AV
        self.payload_after_id_and_meta = [
            metric.Metric.StateFlags3p0(
                FLIGHT_STATE_,
                DUAL_BOARD_CONNECTIVITY_STATE_FLAG,
                RECOVERY_CHECK_COMPLETE_AND_FLIGHT_READY,
                GPS_FIX_FLAG,
                PAYLOAD_CONNECTION_FLAG,
                CAMERA_CONTROLLER_CONNECTION,
            ),
            metric.Metric.ACCEL_LOW_X(ACCEL_LOW_X),
            metric.Metric.ACCEL_LOW_Y(ACCEL_LOW_Y),
            metric.Metric.ACCEL_LOW_Z(ACCEL_LOW_Z),
            metric.Metric.ACCEL_HIGH_X(ACCEL_HIGH_X),
            metric.Metric.ACCEL_HIGH_Y(ACCEL_HIGH_Y),
            metric.Metric.ACCEL_HIGH_Z(ACCEL_HIGH_Z),
            metric.Metric.GYRO_X(GYRO_X),
            metric.Metric.GYRO_Y(GYRO_Y),
            metric.Metric.GYRO_Z(GYRO_Z),
            metric.Metric.ALTITUDE(ALTITUDE),
            metric.Metric.VELOCITY(VELOCITY),
            metric.Metric.continuityCheckResultsApogee(
                APOGEE_PRIMARY_TEST_COMPETE,
                APOGEE_SECONDARY_TEST_COMPETE,
                APOGEE_PRIMARY_TEST_RESULTS,
                APOGEE_SECONDARY_TEST_RESULTS,
            ),
            metric.Metric.continuityCheckResultsMain(
                MAIN_PRIMARY_TEST_COMPETE,
                MAIN_SECONDARY_TEST_COMPETE,
                MAIN_PRIMARY_TEST_RESULTS,
                MAIN_SECONDARY_TEST_RESULTS,
            ),
            metric.Metric.MovingToBroadCastFlag(MOVE_TO_BROADCAST),
            # Note the dummy byte here for TBC purposes
            metric.Metric.dummyByte(),
        ]


class AVtoGCSData2(MockPacket):
    def __init__(
        self,
        RSSI: float = 0.0,
        SNR: float = 62,
        FLIGHT_STATE_: int = 0,
        DUAL_BOARD_CONNECTIVITY_STATE_FLAG=False,
        RECOVERY_CHECK_COMPLETE_AND_FLIGHT_READY=False,
        GPS_FIX_FLAG=False,
        PAYLOAD_CONNECTION_FLAG=True,
        CAMERA_CONTROLLER_CONNECTION=True,
        LATITUDE=-37.80808500000,
        LONGITUDE=144.96507800000,
        NAV_STATUS="G2",
        QW=0,
        QX=1,
        QY=-1,
        QZ=0.5,
    ):
        super().__init__()
        self.ID = 0x04
        self.RSSI = RSSI
        self.SNR = SNR
        self.ORIGIN_DEVICE = MockPacket._SourceDevice.AV
        self.payload_after_id_and_meta = [
            metric.Metric.StateFlags3p0(
                FLIGHT_STATE_,
                DUAL_BOARD_CONNECTIVITY_STATE_FLAG,
                RECOVERY_CHECK_COMPLETE_AND_FLIGHT_READY,
                GPS_FIX_FLAG,
                PAYLOAD_CONNECTION_FLAG,
                CAMERA_CONTROLLER_CONNECTION,
            ),
            metric.Metric.GPS(LATITUDE, LONGITUDE),
            metric.Metric.NAVIGATION_STATUS(NAV_STATUS),
            metric.Metric.QUATERNION(QW),
            metric.Metric.QUATERNION(QX),
            metric.Metric.QUATERNION(QY),
            metric.Metric.QUATERNION(QZ),
        ]


class AVtoGCSData3(MockPacket):
    def __init__(
        self,
        RSSI: float = 0.0,
        SNR: float = 63,
        FLIGHT_STATE_: int = 0,
        DUAL_BOARD_CONNECTIVITY_STATE_FLAG=False,
        RECOVERY_CHECK_COMPLETE_AND_FLIGHT_READY=False,
        GPS_FIX_FLAG=False,
        PAYLOAD_CONNECTION_FLAG=True,
        CAMERA_CONTROLLER_CONNECTION=True,
    ):
        super().__init__()
        self.ID = 0x05
        self.RSSI = RSSI
        self.SNR = SNR
        self.ORIGIN_DEVICE = MockPacket._SourceDevice.AV
        self.payload_after_id_and_meta = [
            metric.Metric.StateFlags3p0(
                FLIGHT_STATE_,
                DUAL_BOARD_CONNECTIVITY_STATE_FLAG,
                RECOVERY_CHECK_COMPLETE_AND_FLIGHT_READY,
                GPS_FIX_FLAG,
                PAYLOAD_CONNECTION_FLAG,
                CAMERA_CONTROLLER_CONNECTION,
            ),
            # TBC for rest of the bytes?
        ] + [metric.Metric.dummyByte()] * 30


# A bit like the GCS class. Just used for context
class GSEDAQData:
    # Wake client threads periodically while waiting (shutdown, spurious wakeups).
    GSE_POLL_S = 1.0
    _labview_ready = threading.Condition()
    latest_labview_data: Optional[bytes] = None
    labview_data_version: int = 0

    @classmethod
    def publish_labview_update(cls, payload: bytes) -> None:
        with cls._labview_ready:
            cls.latest_labview_data = payload
            cls.labview_data_version += 1
            cls._labview_ready.notify_all()

    @classmethod
    def wait_new_labview_payload(
        cls, after_version: int
    ) -> Optional[Tuple[bytes, int]]:
        """Block until ``labview_data_version > after_version`` or shutdown."""
        with cls._labview_ready:
            while True:
                if service_helper.time_to_stop():
                    return None
                if (
                    cls.latest_labview_data is not None
                    and cls.labview_data_version > after_version
                ):
                    return cls.latest_labview_data, cls.labview_data_version
                cls._labview_ready.wait(timeout=cls.GSE_POLL_S)

    @classmethod
    def shutdown_wake_clients(cls) -> None:
        with cls._labview_ready:
            cls._labview_ready.notify_all()


def sinusoid(
    t: float,
    min: float,
    max: float,
    period: float,
    phase: float,
    apply_noise: bool = True,
) -> float:
    """Generate sinusoidal value for simulation purposes

    Args:
        t (float): Time in seconds
        min (float): Min y value
        max (float): Max y value
        period (float): Period in seconds
        phase (float): Phase in radians
        apply_noise (bool, optional): Apply fake signal noise. Defaults to True.

    Returns:
        float: Output value
    """

    amplitude = (max - min) / 2
    offset = (max + min) / 2
    base = amplitude * math.sin(2 * math.pi * (t / period) + phase) + offset

    if apply_noise:
        noise_range_abs = amplitude * MockPacket._NOISE_COEFFICIENT
        base *= 1 - MockPacket._NOISE_COEFFICIENT  # Make space for noise
        noise = (
            MockPacket._NOISE_COEFFICIENT * random.random() * noise_range_abs
        )
        return base + noise

    return base


def changing_int(t: float, min: int, max: int, wait_time_s: float):
    """Output an int from `min` to `max` increimenting every `wait_time_s` seconds"""
    span = max - min + 1
    step = int(t // wait_time_s) % span
    return min + step


def changing_bool(t: float, wait_time_s: float = 1):
    """Bool changing every `wait_time_s` seconds"""
    return t % wait_time_s * 2 > wait_time_s


def corrupt_packet(
    packet: dict, corruption_chance: float = 0.01, max_corruption: float = 0.3
):
    """Corrupts data inside a packet with random bit flips

    Args:
        packet (dict): Packet data to be corrupted
        corruption_chance (float): Chance of packet being corrupted [0, 1]
        max_corruption (float): Max percentage of bits flipped [0, 1]
    """
    assert (
        0 <= corruption_chance <= 1
    ), "Corruption chance must be between 0 and 1"
    assert 0 <= max_corruption <= 1, "Max corruption must be between 0 and 1"

    if random.random() <= corruption_chance:
        corruption = max_corruption * random.random()

        for key, value in packet.items():
            data_type = type(value)

            # Get packed bits of value
            packed = None
            if isinstance(value, bool):
                packed = struct.pack("?", value)
            elif isinstance(value, int):
                packed = struct.pack("i", value)
            elif isinstance(value, float):
                packed = struct.pack("f", value)

            # Only flip bits of supported value types
            if packed != None:
                binary_str = "".join(f"{byte:08b}" for byte in packed)
                bytes_str = bytes(
                    int(binary_str[i: i + 8], 2)
                    for i in range(0, len(binary_str), 8)
                )

                # Generate corruption mask to flip bits based on corruption % chance
                binary_corrupt = "".join(
                    random.choices(
                        ["1", "0"],
                        weights=[corruption, 1 - corruption],
                        k=len(binary_str),
                    )
                )
                bytes_corrupt = bytes(
                    int(binary_corrupt[i: i + 8], 2)
                    for i in range(0, len(binary_corrupt), 8)
                )
                byte_data = bytes(
                    a ^ b for a, b in zip(bytes_str, bytes_corrupt)
                )

                # Pack bits back into a value
                if data_type == bool:
                    value_corrupt = struct.unpack("?", byte_data)[0]
                elif data_type == int:
                    value_corrupt = struct.unpack("i", byte_data)[0]
                    value_corrupt &= (1 << value.bit_length()) - 1
                elif data_type == float:
                    value_corrupt = struct.unpack("f", byte_data)[0]
                    if not Metric.is_valid_float32(value_corrupt):
                        value_corrupt = 3.4028235e38

                # Add corrupt value to packet
                packet[key] = value_corrupt


def get_sinusoid_packets_av(
    START_TIME: float, EXPERIMENTAL: bool, CORRUPTION: bool
) -> List[MockPacket]:
    """Just generate packets with sinusoidal values over time.
    Values ranges should cover optimal operating conditions unless specified otherwise

    Args:
        START_TIME (float): A constant monotonic time value in seconds since the start of the program.
        EXPERIMENTAL (bool): If True, use values that indicate erroneous operation

    Returns:
        List[MockPacket]: A list of all simulated packet types
    """

    TIME_NOW = time.monotonic()
    T = TIME_NOW - START_TIME

    ARGS_AV_COMMON = {
        "RSSI": sinusoid(T, min=-50, max=0, period=10, phase=0),
        "SNR": sinusoid(T, min=0, max=10, period=10, phase=math.pi / 2),
        "FLIGHT_STATE_": (
            changing_int(T, 0, 0b111, 1) if EXPERIMENTAL else 0b000
        ),
        "DUAL_BOARD_CONNECTIVITY_STATE_FLAG": (
            changing_bool(T) if EXPERIMENTAL else True
        ),
        "RECOVERY_CHECK_COMPLETE_AND_FLIGHT_READY": (
            changing_bool(T) if EXPERIMENTAL else False
        ),
        "GPS_FIX_FLAG": changing_bool(T) if EXPERIMENTAL else True,
        "PAYLOAD_CONNECTION_FLAG": changing_bool(T) if EXPERIMENTAL else True,
        "CAMERA_CONTROLLER_CONNECTION": (
            changing_bool(T) if EXPERIMENTAL else True
        ),
    }

    ARGS_AVtoGCSData1 = ARGS_AV_COMMON | {
        "ACCEL_LOW_X": int(
            2048
            * sinusoid(T, min=-15.9, max=15.9, period=5, phase=2 * math.pi / 3)
        ),
        "ACCEL_LOW_Y": int(
            2048
            * sinusoid(T, min=-15.9, max=15.9, period=5, phase=4 * math.pi / 3)
        ),
        "ACCEL_LOW_Z": -int(
            2048
            * sinusoid(T, min=-15.9, max=15.9, period=5, phase=6 * math.pi / 3)
        ),
        "ACCEL_HIGH_X": -int(
            1024 * sinusoid(T, min=-32, max=32, period=5,
                            phase=2 * math.pi / 3)
        ),
        "ACCEL_HIGH_Y": -int(
            1024 * sinusoid(T, min=-32, max=32, period=5,
                            phase=4 * math.pi / 3)
        ),
        "ACCEL_HIGH_Z": int(
            1024 * sinusoid(T, min=-32, max=32, period=5,
                            phase=6 * math.pi / 3)
        ),
        # should be [-30,30] on output
        "GYRO_X": int(
            sinusoid(T, min=-245, max=245, period=5, phase=2 * math.pi / 3)
            / 0.00875
        ),
        "GYRO_Y": int(
            sinusoid(T, min=-245, max=245, period=5, phase=4 * math.pi / 3)
            / 0.00875
        ),
        "GYRO_Z": int(
            sinusoid(T, min=-245, max=245, period=5, phase=6 * math.pi / 3)
            / 0.00875
        ),
        "ALTITUDE": sinusoid(T, min=0, max=3000, period=40, phase=0),
        "VELOCITY": sinusoid(T, min=0, max=350, period=20, phase=0),
        "APOGEE_PRIMARY_TEST_COMPETE": (
            changing_bool(T) if EXPERIMENTAL else False
        ),
        "APOGEE_SECONDARY_TEST_COMPETE": (
            changing_bool(T) if EXPERIMENTAL else False
        ),
        "APOGEE_PRIMARY_TEST_RESULTS": (
            changing_bool(T) if EXPERIMENTAL else False
        ),
        "APOGEE_SECONDARY_TEST_RESULTS": (
            changing_bool(T) if EXPERIMENTAL else False
        ),
        "MAIN_PRIMARY_TEST_COMPETE": (
            changing_bool(T) if EXPERIMENTAL else False
        ),
        "MAIN_SECONDARY_TEST_COMPETE": (
            changing_bool(T) if EXPERIMENTAL else False
        ),
        "MAIN_PRIMARY_TEST_RESULTS": (
            changing_bool(T) if EXPERIMENTAL else False
        ),
        "MAIN_SECONDARY_TEST_RESULTS": (
            changing_bool(T) if EXPERIMENTAL else False
        ),
        "MOVE_TO_BROADCAST": changing_bool(T) if EXPERIMENTAL else False,
    }

    if EXPERIMENTAL:
        nav_status = Metric.POSSIBLE_NAV_VALUES[
            int(T / 1 % len(Metric.POSSIBLE_NAV_VALUES))
        ]
    else:
        nav_status = "G2"
        assert (
            nav_status in Metric.POSSIBLE_NAV_VALUES
        ), f"Invalid NAV_STATUS: {nav_status}"

    ARGS_AVtoGCSData2 = ARGS_AV_COMMON | {
        "LATITUDE": sinusoid(
            T,
            min=-37.80808500000 - 0.1,
            max=37.80808500000 + 0.1,
            period=10,
            phase=0,
        ),
        "LONGITUDE": sinusoid(
            T,
            min=144.96507800000 - 0.1,
            max=144.96507800000 + 0.1,
            period=10,
            phase=0,
        ),
        "NAV_STATUS": nav_status,
        "QW": sinusoid(T, min=-1, max=1, period=3, phase=1 * 2 * math.pi / 4),
        "QX": sinusoid(T, min=-1, max=1, period=4, phase=2 * 2 * math.pi / 4),
        "QY": sinusoid(T, min=-1, max=1, period=5, phase=3 * 2 * math.pi / 4),
        "QZ": sinusoid(T, min=-1, max=1, period=6, phase=4 * 2 * math.pi / 4),
    }

    ARGS_AVtoGCSData3 = ARGS_AV_COMMON

    # Simulate random data corruption on packet
    if CORRUPTION:
        corrupt_packet(ARGS_AVtoGCSData1)
        corrupt_packet(ARGS_AVtoGCSData2)
        corrupt_packet(ARGS_AVtoGCSData3)

    # Do not emulate GSE packets until new emulation is supported
    return [
        AVtoGCSData1(**ARGS_AVtoGCSData1),
        AVtoGCSData2(**ARGS_AVtoGCSData2),
        AVtoGCSData3(**ARGS_AVtoGCSData3),
    ]


def get_sinusoid_packets_gsedaq(
    START_TIME: float, EXPERIMENTAL: bool, CORRUPTION: bool
) -> GseDaqMetrics:
    """Generates sinusoidal packets of GSE data"""

    TIME_NOW = time.monotonic()
    T = TIME_NOW - START_TIME

    values = {
        "temp_tank_top": sinusoid(
            T, min=-10, max=50, period=10, phase=1 * 2 * math.pi / 4
        ),
        "temp_tank_middle": sinusoid(
            T, min=-20, max=40, period=10, phase=1 * 2 * math.pi / 4
        ),
        "temp_tank_bottom": sinusoid(
            T, min=-30, max=30, period=10, phase=1 * 2 * math.pi / 4
        ),
        "temp_vent": sinusoid(
            T, min=-90, max=25, period=10, phase=1 * 2 * math.pi / 4
        ),
        "temp_pipe_n2o_gse": sinusoid(
            T, min=-20, max=20, period=10, phase=1 * 2 * math.pi / 4
        ),
        "pressure_n2o_bottle": sinusoid(
            T, min=1, max=60, period=10, phase=1 * 2 * math.pi / 4
        ),
        "pressure_n2o_tank": sinusoid(
            T, min=1, max=60, period=10, phase=-1 * 2 * math.pi / 4
        ),
        "pressure_o2_tank": sinusoid(
            T, min=40, max=60, period=10, phase=1 * 2 * math.pi / 4
        ),
        "weight_rocket": sinusoid(
            T, min=0, max=10, period=10, phase=1 * 2 * math.pi / 4
        ),
    }

    if CORRUPTION:
        corrupt_packet(values)

    return GseDaqMetrics(**values)


def gse_client_manager(conn, addr):
    slogger.debug(f"Connected to new GSE/GDAQ TCP client {addr}.")
    last_version = -1
    try:
        while not service_helper.time_to_stop():
            got = GSEDAQData.wait_new_labview_payload(last_version)
            if got is None:
                break
            payload, version = got
            try:
                conn.sendall(payload)
            except (ConnectionResetError, BrokenPipeError, OSError):
                break
            last_version = version
    finally:
        conn.close()
    slogger.debug(f"Closed GSE/DAQ TCP client {addr}.")


def gse_server_manager(
    port: int, start_time: float, experimental: bool, corruption: bool
):
    host = "127.0.0.1"
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    slogger.info(f"Emulation labview server is LISTENING on {host}:{port}")
    all_threads: List[threading.Thread] = []
    try:
        while not service_helper.time_to_stop():
            metrics = get_sinusoid_packets_gsedaq(
                start_time, experimental, corruption
            )
            enabled_map = GseDaqMetrics.get_gse_sensor_enabled_map()
            row_dict = GseDaqMetrics.build_labview_row_dict(
                asdict(metrics), enabled_map
            )
            row_xml = GseDaqMetrics.build_xml_row(row_dict)
            GSEDAQData.publish_labview_update(
                row_xml.encode("utf-8") + b"\n"
            )

            time.sleep(MockPacket.TIME_INBETWEEN_PACKETS)

            server.settimeout(0.0)
            while not service_helper.time_to_stop():
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    break
                except OSError:
                    break

                thread = threading.Thread(
                    target=gse_client_manager, args=(conn, addr)
                )
                all_threads.append(thread)
                thread.start()
                slogger.debug(f"Started new TCP thread for {addr}")

    finally:
        GSEDAQData.shutdown_wake_clients()
        try:
            server.close()
        except OSError:
            pass

    for t in all_threads:
        t.join()


def main():
    slogger.debug("Emulator starting")

    try:
        FAKE_DEVICE_NAME = sys.argv[sys.argv.index("--device-rocket") + 1]
        INTERFACE_TYPE = get_interface_type(
            sys.argv[sys.argv.index("--interface-type") + 1]
        )
    except ValueError:
        slogger.error("Failed to find device names in arguments for emulator")
        raise

    experimental_cli_override = "--experimental" in sys.argv
    corruption_cli_override = "--corruption" in sys.argv

    MockPacket.initialize_settings(
        config.get_config()["emulation"],
        FAKE_DEVICE_NAME=FAKE_DEVICE_NAME,
        INTERFACE_TYPE=INTERFACE_TYPE,
    )

    # Always consider the implications of writing GCSto* packets.
    # They are not recieved by the GCS

    # Used for the sequence lock class GSE debugging
    CONFIG_LOADED = config.get_config()
    AV_LOCK_PATH = CONFIG_LOADED["locks"]["lock_file_av_response_path"]

    START_TIME = time.monotonic()
    last_time_av_written = START_TIME
    last_time_av_warned = START_TIME

    LOCK_WARNING_TIME = 5

    EXPERIMENTAL = (
        experimental_cli_override
        or CONFIG_LOADED["emulation"]["experimental"].lower() == "true"
    )

    CORRUPTION = corruption_cli_override

    if EXPERIMENTAL:
        slogger.warning(
            "Experimental mode enabled. Values may appear nonsensical."
        )

    # Start a thread to send the GSE information with a standalone TCP server
    gse_server_port = int(config.get_config()["emulation"]["tcp_server_port"])
    gse_server_manager_thread = threading.Thread(
        target=gse_server_manager,
        args=(gse_server_port, START_TIME, EXPERIMENTAL, CORRUPTION),
    )
    gse_server_manager_thread.start()

    # This thread will now do the AV half duplex emulation

    while not service_helper.time_to_stop():
        for packet in get_sinusoid_packets_av(
            START_TIME, EXPERIMENTAL, CORRUPTION
        ):
            device = packet.ORIGIN_DEVICE
            # As a cheeky sequence emulation, only write when the lock file is PRESENT
            if random.random() < MockPacket._PACKET_LOSS:
                continue
            match device:
                case MockPacket._SourceDevice.AV:
                    if os.path.exists(AV_LOCK_PATH):
                        packet.write_payload()
                        last_time_av_written = time.monotonic()
                        time.sleep(MockPacket.TIME_INBETWEEN_PACKETS)
                case MockPacket._SourceDevice.GCS:
                    packet.write_payload()
                    time.sleep(MockPacket.TIME_INBETWEEN_PACKETS)
        # Warn if locks are present for too long. Possible deadlock while in dev

        check_time = time.monotonic()
        AV_AWAIT_TIME = check_time - last_time_av_written
        if (
            AV_AWAIT_TIME
        ) > LOCK_WARNING_TIME and check_time - last_time_av_warned > 3:
            slogger.warning(
                f"AV emulation awaiting server sequence timing for {round(AV_AWAIT_TIME)} seconds"
            )
            last_time_av_warned = check_time

    gse_server_manager_thread.join()
    slogger.debug("Emulator finished")


if __name__ == "__main__":
    # This only runs if you start this as a service directly. Not for imports
    main()
