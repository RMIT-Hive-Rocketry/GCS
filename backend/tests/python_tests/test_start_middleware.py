"""Unit tests for middleware argv building (build_middleware_argv)."""

import pytest

from cli.start_middleware import (
    InterfaceType,
    build_middleware_argv,
)


FAKE_BINARY = "/fake/path/middleware_debug"
PENDANT = "gcs_rocket"
WEB = "/tmp/gcs_rocket_web_pull.sock"

LORA_CONFIG = {
    "frequency": "928",
    "spread_factor": "SF9",
    "bandwidth": "500",
    "tx_preamble": "12",
    "rx_preamble": "16",
    "power": "22",
    "crc": "OFF1",  # Technically you can only pass OFF or ON
    "iq": "OFF2",
    "net": "OFF3",
}


def test_build_middleware_argv_single_tcp():
    argv = build_middleware_argv(
        FAKE_BINARY,
        release=False,
        INTERFACE_TYPE=InterfaceType.TCP,
        DEVICE_PATH="192.168.1.1:9000",
        PENDANT_SOCKET_PATH=PENDANT,
        WEB_CONTROL_SOCKET_PATH=WEB,
    )
    assert argv[0] == FAKE_BINARY
    assert argv[1] == "TCP"
    assert argv[2] == "192.168.1.1:9000"
    assert argv[3] == PENDANT
    assert argv[4] == WEB
    assert len(argv) == 5


def test_build_middleware_argv_single_test():
    argv = build_middleware_argv(
        FAKE_BINARY,
        release=False,
        INTERFACE_TYPE=InterfaceType.TEST,
        DEVICE_PATH="/dev/pts/1",
        PENDANT_SOCKET_PATH=PENDANT,
        WEB_CONTROL_SOCKET_PATH=WEB,
    )
    assert argv[1] == "TEST"
    assert argv[2] == "/dev/pts/1"
    assert len(argv) == 5


def test_build_middleware_argv_single_test_uart():
    argv = build_middleware_argv(
        FAKE_BINARY,
        release=False,
        INTERFACE_TYPE=InterfaceType.TEST_UART,
        DEVICE_PATH="/dev/pts/2",
        PENDANT_SOCKET_PATH=PENDANT,
        WEB_CONTROL_SOCKET_PATH=WEB,
    )
    assert argv[1] == "TEST_UART"
    assert argv[2] == "/dev/pts/2"
    assert len(argv) == 5


def test_build_middleware_argv_single_uart_requires_lora_config():
    with pytest.raises(ValueError, match="UART interface requires lora_config"):
        build_middleware_argv(
            FAKE_BINARY,
            release=False,
            INTERFACE_TYPE=InterfaceType.UART,
            DEVICE_PATH="/dev/serial0",
            PENDANT_SOCKET_PATH=PENDANT,
            WEB_CONTROL_SOCKET_PATH=WEB,
            lora_config=None,
        )


def test_build_middleware_argv_single_uart_with_lora():
    argv = build_middleware_argv(
        FAKE_BINARY,
        release=False,
        INTERFACE_TYPE=InterfaceType.UART,
        DEVICE_PATH="/dev/serial0",
        PENDANT_SOCKET_PATH=PENDANT,
        WEB_CONTROL_SOCKET_PATH=WEB,
        lora_config=LORA_CONFIG,
    )
    assert argv[0] == FAKE_BINARY
    assert argv[1] == "UART"
    assert argv[2] == "/dev/serial0"
    assert argv[3] == PENDANT
    assert argv[4] == WEB
    # UART adds 9 lora params in order
    assert argv[5] == LORA_CONFIG["frequency"]
    assert argv[6] == LORA_CONFIG["spread_factor"]
    assert argv[7] == LORA_CONFIG["bandwidth"]
    assert argv[8] == LORA_CONFIG["tx_preamble"]
    assert argv[9] == LORA_CONFIG["rx_preamble"]
    assert argv[10] == LORA_CONFIG["power"]
    assert argv[11] == LORA_CONFIG["crc"]
    assert argv[12] == LORA_CONFIG["iq"]
    assert argv[13] == LORA_CONFIG["net"]
    assert len(argv) == 14


def test_build_middleware_argv_opt_arg_gse_only():
    argv = build_middleware_argv(
        FAKE_BINARY,
        release=False,
        INTERFACE_TYPE=InterfaceType.TCP,
        DEVICE_PATH="127.0.0.1:9000",
        PENDANT_SOCKET_PATH=PENDANT,
        WEB_CONTROL_SOCKET_PATH=WEB,
        opt_arg="--GSE_ONLY",
    )
    assert argv[-1] == "--GSE_ONLY"
    assert len(argv) == 6


def test_build_middleware_argv_uart_plus_opt_arg():
    argv = build_middleware_argv(
        FAKE_BINARY,
        release=False,
        INTERFACE_TYPE=InterfaceType.UART,
        DEVICE_PATH="/dev/serial0",
        PENDANT_SOCKET_PATH=PENDANT,
        WEB_CONTROL_SOCKET_PATH=WEB,
        lora_config=LORA_CONFIG,
        opt_arg="--GSE_ONLY",
    )
    assert argv[-1] == "--GSE_ONLY"
    assert len(argv) == 15


def test_build_middleware_argv_ordering():
    """Assert fixed order: binary, type, device, pendant, web, [lora], [opt]."""
    argv = build_middleware_argv(
        FAKE_BINARY,
        release=True,
        INTERFACE_TYPE=InterfaceType.TEST,
        DEVICE_PATH="/dev/pty/0",
        PENDANT_SOCKET_PATH="pendant_sock",
        WEB_CONTROL_SOCKET_PATH="web_sock",
        opt_arg="--GSE_ONLY",
    )
    assert argv == [
        FAKE_BINARY,
        "TEST",
        "/dev/pty/0",
        "pendant_sock",
        "web_sock",
        "--GSE_ONLY",
    ]


def test_build_middleware_argv_rejects_non_interface_type():
    with pytest.raises(ValueError, match="INTERFACE_TYPE must be a InterfaceType"):
        build_middleware_argv(
            FAKE_BINARY,
            release=False,
            INTERFACE_TYPE="TCP",  # type: ignore[arg-type]
            DEVICE_PATH="/dev/null",
            PENDANT_SOCKET_PATH=PENDANT,
            WEB_CONTROL_SOCKET_PATH=WEB,
        )
