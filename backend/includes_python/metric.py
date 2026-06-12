from typing import Annotated, Literal
import math
import struct
import backend.includes_python.process_logging as slogger


class Metric:
    """The metric class will generate byte payloads to be used by the device emulator.
    AFAIK everything is big endian"""

    SIGNED_INT = Annotated[int, Literal["signed"]]
    UNSIGNED_INT = Annotated[int, Literal["unsigned"]]

    # Using list for iterating over these values in emulator
    POSSIBLE_NAV_VALUES = ["NF", "DR", "G2", "G3", "D2", "D3", "RK", "TT"]

    @staticmethod
    def to_visible_repr(s) -> str:
        """Print a string in a visible representation, escaping non-printable characters."""
        if len(s) <= 0:
            return "<empty>"
        out = []
        for c in s:
            codepoint = ord(c)
            # Printable ASCII or extended ASCII (0x00-0xFF) only, and printable
            if codepoint <= 0xFF and c.isprintable():
                out.append(c)
            else:
                if codepoint <= 0xFF:
                    out.append(f"\\x{codepoint:02x}")
                elif codepoint <= 0xFFFF:
                    out.append(f"\\u{codepoint:04x}")
                else:
                    out.append(f"\\U{codepoint:08x}")
        return "".join(out)

    @staticmethod
    def _invert_bits(num: int) -> int:
        num_bits = (
            num.bit_length()
        )  # Get the number of bits required to represent num
        # Create a bitmask of the same length (all 1s)
        mask = (1 << num_bits) - 1
        return ~num & mask  # Invert bits and apply mask

    @staticmethod
    def _invert_byte(data: bytes) -> bytes:
        if len(data) != 1:
            raise ValueError("Input must be a single byte.")
        return bytes([~data[0] & 0xFF])

    @staticmethod
    def _float_to_bytes(
        value: float, num_bytes: int = 4, little_endian: bool = False
    ) -> bytes:
        """Converts a float to bytes (default 32-bit/4 bytes).

        Args:
            value (float): The float value to convert
            num_bytes (int): Number of bytes (4 for float32, 8 for float64)

        Returns:
            bytes: The float represented as bytes

        Raises:
            ValueError: If num_bytes is not 4 (float32) or 8 (float64)
        """
        mode = "<" if little_endian else ">"
        if num_bytes == 4:
            # https://docs.python.org/3/library/struct.html#byte-order-size-and-alignment
            return struct.pack(f"{mode}f", value)
        if num_bytes == 8:  # Double?
            return struct.pack(f"{mode}d", value)

        raise ValueError("num_bytes must be 4 (float32) or 8 (float64)")

    @staticmethod
    def _float32_to_bytes(value: float, little_endian: bool = False) -> bytes:
        """Converts a float to a 32-bit (4 byte) representation.

        Args:
            value (float): The float value to convert

        Returns:
            bytes: The float32 represented as 4 bytes

        Raises:
            ValueError: If value cannot be represented as float32
        """
        if not Metric.is_valid_float32(value):
            raise ValueError("Value must be a valid 32-bit float")

        return Metric._float_to_bytes(value, 4, little_endian)

    @staticmethod
    def _float64_to_bytes(value: float) -> bytes:
        """Converts a float to a 64-bit (8 byte) representation.

        Args:
            value (float): The float value to convert

        Returns:
            bytes: The float64 represented as 8 bytes
        """
        return Metric._float_to_bytes(value, 8)

    @staticmethod
    def _int_to_byte_unsigned(value: int) -> bytes:
        """Converts an unsigned integer to a single byte (8 bits).

        Args:
            value (int): The unsigned integer to convert (0-255).

        Returns:
            bytes: The integer represented as a single byte.

        Raises:
            ValueError: If value is outside the valid unsigned byte range.
        """
        if not (0 <= value <= 0xFF):  # 0xFF == 255 (8-bit max)
            raise ValueError(
                f"Value must be between 0 and 255 (8-bit unsigned range). Got: {value}"
            )
        return value.to_bytes(1, byteorder="big", signed=False)

    @staticmethod
    def _int_to_byte_signed(value: int) -> bytes:
        """Converts a signed integer to a single byte (8 bits).

        Args:
            value (int): The signed integer to convert (-128 to 127).

        Returns:
            bytes: The integer represented as a single byte.

        Raises:
            ValueError: If value is outside the valid signed byte range.
        """
        if not (-128 <= value <= 127):
            raise ValueError(
                f"Value must be between -128 and 127 (8-bit signed range). Got: {value}"
            )
        return value.to_bytes(1, byteorder="big", signed=True)

    @staticmethod
    def _int_to_multiple_bytes_unsigned(value: int, num_bytes: int) -> bytes:
        """Converts an unsigned integer to a specified number of bytes.

        Args:
            value (int): The unsigned integer to convert.
            NUM_BYTES (int): The number of bytes to convert the integer into.

        Returns:
            bytes: The integer represented as bytes.

        Raises:
            ValueError: If the value is out of range for the specified number of bytes.
        """
        max_value = (1 << (8 * num_bytes)) - 1

        if not (0 <= value <= max_value):
            raise ValueError(
                f"Value must be between 0 and {max_value} for {num_bytes} byte(s). Got: {value}"
            )

        return value.to_bytes(num_bytes, byteorder="big", signed=False)

    @staticmethod
    def _int_to_multiple_bytes_signed(value: int, num_bytes: int) -> bytes:
        """Converts a signed integer to a specified number of bytes.

        Args:
            value (int): The signed integer to convert.
            num_bytes (int): The number of bytes to convert the integer into.

        Returns:
            bytes: The integer represented as bytes.

        Raises:
            ValueError: If the value is out of range for the specified number of bytes.
        """
        max_value = (1 << (8 * num_bytes - 1)) - 1
        min_value = -(1 << (8 * num_bytes - 1))

        if not (min_value <= value <= max_value):
            raise ValueError(
                f"Value must be between {min_value} and {max_value} for {num_bytes} byte(s). Got: {value}"
            )

        return value.to_bytes(num_bytes, byteorder="big", signed=True)

    @staticmethod
    def is_valid_int3_(value) -> bool:
        """Check if a value is within the valid range of an unsigned 3-bit integer."""
        if not isinstance(value, int):
            return False
        return 0b000 <= value <= 0b111

    @staticmethod
    def is_valid_int16_signed(value) -> bool:
        """Check if a value is within the valid range of a signed 2-byte integer (int16)."""
        if not isinstance(value, int):
            return False
        return -32_768 <= value <= 32_767

    @staticmethod
    def is_valid_int16_unsigned(value) -> bool:
        """Check if a value is within the valid range of an unsigned 2-byte integer (uint16)."""
        if not isinstance(value, int):
            return False
        return 0 <= value <= 65_535

    @staticmethod
    def is_valid_float32(value) -> bool:
        """Check if a value is within the valid range of a 32-bit float. All floats are signed

        Args:
            value (float): The value to check.

        Returns:
            bool: True if the value is a valid 32-bit float, False otherwise.
        """
        if not isinstance(value, (int, float)):
            return False
        return (
            -3.4028235e38 <= value <= 3.4028235e38
            and not math.isinf(value)
            and not math.isnan(value)
        )

    @staticmethod
    def is_valid_float64(value) -> bool:
        """Check if a value is within the valid range of a 64-bit float.

        Args:
            value (float): The value to check.

        Returns:
            bool: True if the value is a valid 64-bit float, False otherwise.
        """
        if not isinstance(value, (int, float)):
            return False
        return not math.isinf(value) and not math.isnan(value)

    @staticmethod
    def dummy_byte() -> bytes:
        """Just returns 0x00"""
        result = 0
        return Metric._int_to_byte_unsigned(result)

    @staticmethod
    def continuity_check_cmd_flags(
        main_secondary_test: bool,
        main_primary_test: bool,
        apogee_secondary_test: bool,
        aprogee_primary_test: bool,
    ) -> bytes:
        """_summary_

        Args:
            main_secondary_test: (0 = Do not do test, 1 = do test)
            main_primary_test: (0 = Do not do test, 1 = do test)
            apogee_secondary_test: (0 = Do not do test, 1 = do test)
            apogee_primary_test: (0 = Do not do test, 1 = do test)

        Returns:
            int: Test flags prefixed with filler bits
        """
        result = 0

        result = (result << 4) | 0b1010  # Add fixed bits
        result = (result << 1) | main_secondary_test
        result = (result << 1) | main_primary_test
        result = (result << 1) | apogee_secondary_test
        result = (result << 1) | aprogee_primary_test

        return Metric._int_to_byte_unsigned(result)

    @staticmethod
    def continuity_check_results_apogee(
        apogee_primary_test_compete: bool,
        apogee_secondary_test_compete: bool,
        apogee_primary_test_results: bool,
        apogee_secondary_test_results: bool,
    ) -> bytes:
        """_summary_

        Note 4

        Args:
            apogee_primary_test_compete (bool): (0 = not complete, 1 = complete)
            apogee_secondary_test_compete (bool): (0 = not complete, 1 = complete)
            apogee_primary_test_results (bool): (0 = No Continuity, 1 = Continuity)
            apogee_secondary_test_results (bool): (0 = No Continuity, 1 = Continuity)

        Returns:
            int: Test flags prefixed with filler bits
        """
        result = 0

        result = (result << 1) | apogee_primary_test_compete
        result = (result << 1) | apogee_secondary_test_compete
        result = (result << 4) | 0b1010  # Add fixed bits
        result = (result << 1) | apogee_primary_test_results
        result = (result << 1) | apogee_secondary_test_results

        return Metric._int_to_byte_unsigned(result)

    @staticmethod
    def continuity_check_results_main(
        main_primary_test_compete: bool,
        main_secondary_test_compete: bool,
        main_primary_test_results: bool,
        main_secondary_test_results: bool,
    ) -> bytes:
        """_summary_

        Note 5

        Args:
            main_primary_test_compete (bool): (0 = not complete, 1 = complete)
            main_secondary_test_compete (bool): (0 = not complete, 1 = complete)
            main_primary_test_results (bool): (0 = No Continuity, 1 = Continuity)
            main_secondary_test_results (bool): (0 = No Continuity, 1 = Continuity)

        Returns:
            int: Test flags prefixed with filler bits
        """
        result = 0

        result = (result << 1) | main_primary_test_compete
        result = (result << 1) | main_secondary_test_compete
        result = (result << 4) | 0b1010  # Add fixed bits
        result = (result << 1) | main_primary_test_results
        result = (result << 1) | main_secondary_test_results

        return Metric._int_to_byte_unsigned(result)

    @staticmethod
    def continuity_check_cmd_flags_inverted(
        main_secondary_test: bool,
        main_primary_test: bool,
        apogee_secondary_test: bool,
        aprogee_primary_test: bool,
    ) -> bytes:
        """Output of regular continuityCheckCMDFlags but every bit is inverted

        Args:
            mainSecondaryTest(bool): (0=Do not do test, 1=do test)
            mainPrimaryTest(bool): (0=Do not do test, 1=do test)
            apogeeSecondaryTest(bool): (0=Do not do test, 1=do test)
            apogeePrimaryTest(bool): (0=Do not do test, 1=do test)

        Returns:
            int: Test flags prefixed with filler bits
        """

        return Metric._invert_byte(
            Metric.continuity_check_cmd_flags(
                main_secondary_test,
                main_primary_test,
                apogee_secondary_test,
                aprogee_primary_test,
            )
        )

    @staticmethod
    def broadcast_begin_cmd_flags(
        begin_braodcast: bool,
    ) -> bytes:
        """_summary_

        Args:
            begin_braodcast (bool): 0 = Do not begin broadcast, 1 = begin broadcast

        Returns:
            bytes: _description_
        """
        result = 0xFF if begin_braodcast else 0x00

        return Metric._int_to_byte_unsigned(result)

    @staticmethod
    def moving_to_broad_cast_flag(
        move_to_braodcast: bool,
    ) -> bytes:
        """

        Note 6

        Args:
            move_to_braodcast (bool): 0 = No not move, 1 = Move to broadcast

        Returns:
            bytes: _description_
        """
        result = 0b10101010 if move_to_braodcast else 0b00000000

        return Metric._int_to_byte_unsigned(result)

    @staticmethod
    def state_set_flag_s2p1(
        sys_on: bool,
        fill_selected: bool,
        ignition_selected: bool,
        n2o_active: bool,
        neutral_active: bool,
        purge_active: bool,
        o2_moment_active: bool,
        ignition_moment_active: bool,  # https://youtu.be/Vmm_Kq1EN8k?si=GEpc8AoEhRgRrFRI
        f9: bool,
        f10: bool,
        f11: bool,
        f12: bool,
    ) -> bytes:
        """_summary_

        Args:
            sys_on: 0 = disable, 1 = enabled
            fill_selected: 0 = no, 1 = yes
            ignition_selected: 0 = no, 1 = yes
            n2o_active: 0 = no, 1 = yes
            neutral_active: 0 = no, 1 = yes
            purge_active: 0 = no, 1 = yes
            o2_moment_active: 0 = no, 1 = yes
            ignition_moment_active: 0 = no, 1 = yes
            f9 (bool): 0 = no, 1 = yes
            f10 (bool): 0 = no, 1 = yes
            f11 (bool): 0 = no, 1 = yes
            f12 (bool): 0 = no, 1 = yes

        Currently ignores the f9, f10, f11 and f12 inputs
        We don't want to send those to the GSE since that'll confuse it

        Returns:
            bytes: _description_
        """

        result = 0
        result = (result << 1) | purge_active
        result = (result << 1) | o2_moment_active
        result = (result << 1) | neutral_active
        result = (result << 1) | n2o_active
        result = (result << 1) | ignition_moment_active
        result = (result << 1) | ignition_selected
        result = (result << 1) | fill_selected
        result = (result << 1) | sys_on

        return Metric._int_to_byte_unsigned(result)

    @staticmethod
    def state_set_flag_inverted_s2p2(
        sys_on: bool,
        fill_selected: bool,
        ignition_selected: bool,
        n2o_active: bool,
        neutral_active: bool,
        purge_active: bool,
        o2_moment_active: bool,
        ignition_moment_active: bool,  # https://youtu.be/Vmm_Kq1EN8k?si=GEpc8AoEhRgRrFRI
        f9: bool,
        f10: bool,
        f11: bool,
        f12: bool,
    ) -> bytes:
        """_summary_

        Args:
            sys_on (bool): 0 = disable, 1 = enabled
            fill_selected (bool): 0 = no, 1 = yes
            ignition_selected (bool): 0 = no, 1 = yes
            n2o_active (bool): 0 = no, 1 = yes
            neutral_active (bool): 0 = no, 1 = yes
            purge_active (bool): 0 = no, 1 = yes
            o2_moment_active (bool): 0 = no, 1 = yes
            ignition_moment_active (bool): 0 = no, 1 = yes
            f9 (bool): 0 = no, 1 = yes
            f10 (bool): 0 = no, 1 = yes
            f11 (bool): 0 = no, 1 = yes
            f12 (bool): 0 = no, 1 = yes

        Returns:
            bytes: _description_
        """

        result = Metric.state_set_flag_s2p1(
            sys_on,
            fill_selected,
            ignition_selected,
            n2o_active,
            neutral_active,
            purge_active,
            o2_moment_active,
            ignition_moment_active,
            f9,
            f10,
            f11,
            f12,
        )

        return Metric._invert_byte(result)

    @staticmethod
    def state_flag_s3p0(
        flight_state_: int,
        dual_board_connectivity_state_flag: bool,
        recovery_check_complete_and_flight_ready: bool,
        gps_fix_flag: bool,
        payload_connection_flag: bool,
        camera_controller_connection: bool,
    ) -> bytes:
        """_summary_

        Note 3, A

        Flight state is a 3 bit number.
        Pass it bit by bit. #lol

        Args:
            flight_state_ (int): See note A
            dual_board_connectivity_state_flag (bool): (0 = Only 1 Board Connected, 1 = 2x Australis Boards Connected)
            recovery_check_complete_and_flight_ready (bool): (0 = not flight ready, 1 = flight ready)
            gps_fix_flag (bool): (0 = No Fix, 1 = Fixed)
            payload_connection_flag (bool): (0 = NC, 1= Connected)
            camera_controller_connection (bool): (0 = NC, 1 = Connected)

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_int3_(flight_state_):
            raise ValueError(
                f"Value must be between 0 and 7 (3-bit unsigned range). Got: {flight_state_}"
            )

        result = 0
        result = (result << 3) | (flight_state_ & 0b111)
        result = (result << 1) | dual_board_connectivity_state_flag
        result = (result << 1) | recovery_check_complete_and_flight_ready
        result = (result << 1) | gps_fix_flag
        result = (result << 1) | payload_connection_flag
        result = (result << 1) | camera_controller_connection

        return Metric._int_to_byte_unsigned(result)

    @staticmethod
    def accel_low_x(
        value: SIGNED_INT,
    ) -> bytes:
        """_summary_

        Args:
            value (SIGNED_INT16): 16bit signed int. Float after calculation

        Returns:
            bytes: _description_
        """
        if not Metric.is_valid_int16_signed(value):
            raise ValueError(
                f"Value must be between -32768 and 32767 (16-bit signed range). Got: {value}"
            )

        return Metric._int_to_multiple_bytes_signed(value, 2)

    @staticmethod
    def accel_low_y(
        value: SIGNED_INT,
    ) -> bytes:
        """_summary_

        Args:
            value (SIGNED_INT16): 16bit signed int. Float after calculation

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_int16_signed(value):
            raise ValueError(
                f"Value must be between -32768 and 32767 (16-bit signed range). Got: {value}"
            )

        return Metric._int_to_multiple_bytes_signed(value, 2)

    @staticmethod
    def accel_low_z(
        value: SIGNED_INT,
    ) -> bytes:
        """_summary_

        Args:
            value (SIGNED_INT16): 16bit signed int. Float after calculation

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_int16_signed(value):
            raise ValueError(
                f"Value must be between -32768 and 32767 (16-bit signed range). Got: {value}"
            )

        return Metric._int_to_multiple_bytes_signed(value, 2)

    @staticmethod
    def accel_high_x(
        value: SIGNED_INT,
    ) -> bytes:
        """_summary_

        Args:
            value (SIGNED_INT16): 16bit signed int. Float after calculation

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_int16_signed(value):
            raise ValueError(
                f"Value must be between -32768 and 32767 (16-bit signed range). Got: {value}"
            )

        return Metric._int_to_multiple_bytes_signed(value, 2)

    @staticmethod
    def accel_high_y(
        value: SIGNED_INT,
    ) -> bytes:
        """_summary_

        Args:
            value (SIGNED_INT16): 16bit signed int. Float after calculation

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_int16_signed(value):
            raise ValueError(
                f"Value must be between -32768 and 32767 (16-bit signed range). Got: {value}"
            )

        return Metric._int_to_multiple_bytes_signed(value, 2)

    @staticmethod
    def accel_high_z(
        value: SIGNED_INT,
    ) -> bytes:
        """_summary_

        Args:
            value (SIGNED_INT16): 16bit signed int. Float after calculation

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_int16_signed(value):
            raise ValueError(
                f"Value must be between -32768 and 32767 (16-bit signed range). Got: {value}"
            )

        return Metric._int_to_multiple_bytes_signed(value, 2)

    @staticmethod
    def gyro_x(
        value: SIGNED_INT,
    ) -> bytes:
        """_summary_

        Args:
            value (SIGNED_INT16): 16bit signed int. Float after calculation

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_int16_signed(value):
            raise ValueError(
                f"Value must be between -32768 and 32767 (16-bit signed range). Got: {value}"
            )

        return Metric._int_to_multiple_bytes_signed(value, 2)

    @staticmethod
    def gyro_y(
        value: SIGNED_INT,
    ) -> bytes:
        """_summary_

        Args:
            value (SIGNED_INT16): 16bit signed int. Float after calculation

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_int16_signed(value):
            raise ValueError(
                f"Value must be between -32768 and 32767 (16-bit signed range). Got: {value}"
            )

        return Metric._int_to_multiple_bytes_signed(value, 2)

    @staticmethod
    def gyro_z(
        value: SIGNED_INT,
    ) -> bytes:
        """_summary_

        Args:
            value (SIGNED_INT16): 16bit signed int. Float after calculation

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_int16_signed(value):
            raise ValueError(
                f"Value must be between -32768 and 32767 (16-bit signed range). Got: {value}"
            )

        return Metric._int_to_multiple_bytes_signed(value, 2)

    @staticmethod
    def altitude(
        value: float,
    ) -> bytes:
        """_summary_

        Args:
            value (float): 32bit float.

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_float32(value):
            raise ValueError("Value must be a valid 32-bit float.")

        return Metric._float32_to_bytes(value)

    @staticmethod
    def velocity(
        value: float,
    ) -> bytes:
        """_summary_

        Args:
            value (float): 32bit float.

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_float32(value):
            raise ValueError("Value must be a valid 32-bit float.")

        return Metric._float32_to_bytes(value)

    @staticmethod
    def gps(latitude: str, longitude: str) -> bytes:
        """GPS coordinate float

        Args:
            latitude (float): 32 bit float
            longitude (float): 32 bit float

        Raises:
            ValueError: Raised if string length != 15

        Returns:
            bytes: Byte output
        """
        if not Metric.is_valid_float32(latitude):
            raise ValueError(
                f"latitude must be a valid 32-bit float.: {latitude}"
            )

        if not Metric.is_valid_float32(longitude):
            raise ValueError(
                f"longitude must be a valid 32-bit float.: {longitude}"
            )

        ba = bytearray()
        ba.extend(Metric._float32_to_bytes(float(latitude), little_endian=True))
        ba.extend(
            Metric._float32_to_bytes(float(longitude), little_endian=True)
        )
        return bytes(ba)

    @staticmethod
    def transducer(
        value: float,
    ) -> bytes:
        """_summary_

        Args:
            value (float): 32bit float.

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_float32(value):
            raise ValueError("Value must be a valid 32-bit float.")

        return Metric._float32_to_bytes(value)

    @staticmethod
    def thermocouple(
        value: float,
    ) -> bytes:
        """_summary_

        Args:
            value (float): 32bit float.

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_float32(value):
            raise ValueError("Value must be a valid 32-bit float.")

        return Metric._float32_to_bytes(value)

    @staticmethod
    def error_code_gse(
        ignition_error: bool,
        relay3_error: bool,
        relay2_error: bool,
        relay1_error: bool,
        thermocouple_4_error: bool,
        thermocouple_3_error: bool,
        thermocouple_2_error: bool,
        thermocouple_1_error: bool,
        load_cell_4_error: bool,
        load_cell_3_error: bool,
        load_cell_2_error: bool,
        load_cell_1_error: bool,
        transducer_4_error: bool,
        transducer_3_error: bool,
        transducer_2_error: bool,
        transducer_1_error: bool,
    ) -> bytes:
        result = 0
        result = (result << 1) | ignition_error
        result = (result << 1) | relay3_error
        result = (result << 1) | relay2_error
        result = (result << 1) | relay1_error
        result = (result << 1) | thermocouple_4_error
        result = (result << 1) | thermocouple_3_error
        result = (result << 1) | thermocouple_2_error
        result = (result << 1) | thermocouple_1_error
        result = (result << 1) | load_cell_4_error
        result = (result << 1) | load_cell_3_error
        result = (result << 1) | load_cell_2_error
        result = (result << 1) | load_cell_1_error
        result = (result << 1) | transducer_4_error
        result = (result << 1) | transducer_3_error
        result = (result << 1) | transducer_2_error
        result = (result << 1) | transducer_1_error

        return Metric._int_to_multiple_bytes_unsigned(result, 2)

    @staticmethod
    def internal_temp_gse(
        value: float,
    ) -> bytes:
        """_summary_

        Args:
            value (float): 32bit float.

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_float32(value):
            raise ValueError("Value must be a valid 32-bit float.")

        return Metric._float32_to_bytes(value)

    @staticmethod
    def wind_speed_gse(
        value: float,
    ) -> bytes:
        """_summary_

        Args:
            value (float): 32bit float.

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_float32(value):
            raise ValueError("Value must be a valid 32-bit float.")

        return Metric._float32_to_bytes(value)

    @staticmethod
    def gas_bottle_weight(
        value: UNSIGNED_INT,
    ) -> bytes:
        """_summary_

        Args:
            value (UNSIGNED_INT16): 16bit unsigned int.

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_int16_unsigned(value):
            raise ValueError(
                f"Value must be between 0, 65_535 (16-bit unsigned range). Got: {value}"
            )

        return Metric._int_to_multiple_bytes_unsigned(value, 2)

    @staticmethod
    def additional_va_input(
        value: float,
    ) -> bytes:
        """_summary_

        Args:
            value (float): 32bit float.

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_float32(value):
            raise ValueError("Value must be a valid 32-bit float.")

        return Metric._float32_to_bytes(value)

    @staticmethod
    def additional_current_input(
        value: float,
    ) -> bytes:
        """_summary_

        Args:
            value (float): 32bit float.  Must be between 4-20mA?

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_float32(value):
            raise ValueError("Value must be a valid 32-bit float.")

        return Metric._float32_to_bytes(value)

    @staticmethod
    def quaternion(
        value: float,
        _override: bool = False,
    ) -> bytes:
        """_summary_

        Args:
            value (float): 32bit float. [-1,1]
            override (bool, optional): If True, allow values outside [-1, 1]. Defaults to False.

        Returns:
            bytes: _description_
        """

        if not Metric.is_valid_float32(value):
            raise ValueError("Value must be a valid 32-bit float.")

        if not (-1 <= value <= 1):
            slogger.warning(
                f"Quaternion is not normalised. You had {value}, need [-1,1]"
            )

        return Metric._float32_to_bytes(value, little_endian=True)

    @staticmethod
    def navigation_status(
        value,
    ) -> bytes:
        """_summary_

        Args:
            value (str): 2 char string
        """
        if not isinstance(value, str):
            raise ValueError("Navigation status must be a string")

        if value not in Metric.POSSIBLE_NAV_VALUES:
            slogger.warning(
                f'Navigation status must be one of: {" ".join(Metric.POSSIBLE_NAV_VALUES)}. Got: {Metric.to_visible_repr(value)}'
            )

        if len(value) != 2:
            raise ValueError("Navigation status must be 2 characters")

        # Encode as UTF-8 because protobuf requires it. Otherwise it will drop packet
        return bytes(value, "utf-8")
