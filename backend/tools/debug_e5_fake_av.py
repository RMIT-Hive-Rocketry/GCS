import argparse
import re
import signal
import time

import serial

from backend.device_emulator import AVtoGCSData1, MockPacket
from cli.start_middleware import InterfaceType

# GENERATED WITH AI FOR DEBUG USE ONLY


def _read_and_print_response(ser: serial.Serial) -> str | None:
    data = ser.read_all()
    if data is None:
        return None

    response = data.decode("utf-8", errors="ignore")
    for line in response.splitlines():
        print(f"> {line}")

    return response


def _send_at_command(
    ser: serial.Serial,
    command: str,
    expected_substring: str | None = None,
    timeout_s: float = 2.0,
) -> str:
    ser.write((command + "\r\n").encode())
    print(f"Sent: {command}")

    response = ""
    started = time.monotonic()
    while True:
        data = ser.read_all()
        if data is not None:
            response += data.decode("utf-8", errors="ignore")

        if expected_substring is None or expected_substring in response:
            break
        if time.monotonic() - started > timeout_s:
            raise TimeoutError(
                f"Timed out waiting for '{expected_substring}' after command '{command}'"
            )
        time.sleep(0.01)

    for line in response.splitlines():
        print(f"> {line}")
    return response


def _extract_rx_payload_hexes(chunk: str) -> list[str]:
    payloads: list[str] = []
    lines = chunk.splitlines()
    expect_hex_next = False
    hex_re = re.compile(r'"([0-9A-Fa-f]+)"')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("+TEST: RX"):
            same_line = hex_re.search(line)
            if same_line:
                payloads.append(same_line.group(1).upper())
                expect_hex_next = False
            else:
                expect_hex_next = True
            continue

        if expect_hex_next:
            next_line = hex_re.search(line)
            if next_line:
                payloads.append(next_line.group(1).upper())
            expect_hex_next = False
            continue

    return payloads


def _build_default_av_to_gcs_data1_hex() -> str:
    if not MockPacket._INITIALISED:
        # Minimal init needed to construct packet class with defaults.
        MockPacket.initialize_settings(
            EMULATION_CONFIG={
                "noise_coefficient": "0.0",
                "packet_loss": "0.0",
            },
            INTERFACE_TYPE=InterfaceType.TEST,
        )

    packet = AVtoGCSData1()
    payload_bytes = packet.get_payload_bytes(EXTERNAL=True)
    return payload_bytes.hex().upper()


def send_fake_av_packets(
    serial_path: str,
    baudrate: int,
    tx_wait_timeout_s: float,
) -> None:
    ser = None
    stop_requested = False

    def _request_stop(signum, _frame) -> None:
        nonlocal stop_requested
        stop_requested = True
        print(f"\nReceived signal {signum}; stopping...")

    old_sigint_handler = signal.getsignal(signal.SIGINT)
    old_sigterm_handler = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)

    try:
        ser = serial.Serial(serial_path, baudrate=baudrate, timeout=1)
        if ser.is_open:
            print(f"Serial port opened: {serial_path} @ {baudrate}")
    except Exception as exc:
        print(f"Failed to open serial port: {exc}")
        signal.signal(signal.SIGINT, old_sigint_handler)
        signal.signal(signal.SIGTERM, old_sigterm_handler)
        return

    at_setup_commands = [
        "AT",
        "AT+MODE=TEST",
        "AT+TEST=RFCFG,915,SF9,500,12,16,22,OFF,OFF,OFF",
        "AT+TEST=?",
    ]

    payload_hex = _build_default_av_to_gcs_data1_hex()
    tx_command = f'AT+TEST=TXLRPKT, "{payload_hex}"'
    print(f"Payload length: {len(payload_hex) // 2} bytes")
    print(f"TX_COMMAND: {tx_command}")

    try:
        for command in at_setup_commands:
            _send_at_command(
                ser=ser,
                command=command,
                expected_substring=None,
                timeout_s=2.0,
            )
            time.sleep(0.2)

        _send_at_command(
            ser=ser,
            command="AT+TEST=RXLRPKT",
            expected_substring="+TEST: RXLRPKT",
            timeout_s=2.0,
        )
        print(
            "Half-duplex fake AV responder started; waiting for command ID 0x01"
        )

        response_count = 0
        prev_time = time.monotonic()
        while not stop_requested:
            data = ser.read_all()
            if not data:
                time.sleep(0.01)
                continue

            rx_chunk = data.decode("utf-8", errors="ignore")
            if not rx_chunk:
                time.sleep(0.01)
                continue

            for line in rx_chunk.splitlines():
                print(f"> {line}")

            for rx_hex in _extract_rx_payload_hexes(rx_chunk):
                if len(rx_hex) < 2:
                    continue

                inbound_id = int(rx_hex[:2], 16)
                print(
                    f"RX payload ID=0x{inbound_id:02X}, len={len(rx_hex) // 2}"
                )
                if inbound_id != 0x01:
                    print("Ignoring non-command packet (expected ID 0x01).")
                    continue

                _send_at_command(
                    ser=ser,
                    command=tx_command,
                    expected_substring="+TEST: TX DONE",
                    timeout_s=tx_wait_timeout_s,
                )
                response_count += 1
                now = time.monotonic()
                delta_ms = (now - prev_time) * 1000.0
                prev_time = now
                print(
                    f"Responded #{response_count:<6d} | diff = {delta_ms:8.2f} ms"
                )

                # Return to RX mode after each TX to stay in half-duplex request/response flow.
                _send_at_command(
                    ser=ser,
                    command="AT+TEST=RXLRPKT",
                    expected_substring="+TEST: RXLRPKT",
                    timeout_s=2.0,
                )
    except Exception as exc:
        print(f"\nError during communication: {exc}")
    finally:
        if ser is not None and ser.is_open:
            ser.close()
        signal.signal(signal.SIGINT, old_sigint_handler)
        signal.signal(signal.SIGTERM, old_sigterm_handler)
        print("Serial port closed.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fake AV flight computer spammer for E5 serial radios."
    )
    parser.add_argument(
        "--serial-path",
        default="/dev/ttyAMA0",
        help="Serial device path (default: /dev/ttyAMA0)",
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        default=230400,
        help="Serial baudrate (default: 230400)",
    )
    parser.add_argument(
        "--tx-wait-timeout-s",
        type=float,
        default=2.0,
        help="Timeout waiting for +TEST: TX DONE (default: 2.0)",
    )
    args = parser.parse_args()

    send_fake_av_packets(
        serial_path=args.serial_path,
        baudrate=args.baudrate,
        tx_wait_timeout_s=args.tx_wait_timeout_s,
    )


if __name__ == "__main__":
    main()
