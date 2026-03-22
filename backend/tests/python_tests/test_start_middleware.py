"""Unit tests for middleware argv building (build_middleware_argv)."""

import pytest

from cli.start_middleware import (
    InterfaceType,
    MiddlewareConfig,
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


def _cfg(
    gse_type: InterfaceType,
    gse_path: str,
    av_type: InterfaceType,
    av_path: str,
    opt_arg: str | None = None,
    lora_config: dict | None = None,
) -> MiddlewareConfig:
    return MiddlewareConfig(
        release=False,
        interface_gse_type=gse_type,
        device_path_gse=gse_path,
        interface_av_type=av_type,
        device_path_av=av_path,
        pendant_socket_path=PENDANT,
        web_control_socket_path=WEB,
        opt_arg=opt_arg,
        lora_config=lora_config,
    )


def test_build_middleware_argv_gse_av_tcp():
    """Single link (same gse and av): TCP."""
    cfg = _cfg(
        InterfaceType.TCP,
        "192.168.1.1:9000",
        InterfaceType.TCP,
        "192.168.1.1:9000",
    )
    argv = build_middleware_argv(cfg, FAKE_BINARY)
    assert argv[0] == FAKE_BINARY
    assert argv[1] == "TCP"
    assert argv[2] == "192.168.1.1:9000"
    assert argv[3] == "TCP"
    assert argv[4] == "192.168.1.1:9000"
    assert argv[5] == PENDANT
    assert argv[6] == WEB
    assert len(argv) == 7


def test_build_middleware_argv_gse_av_test():
    """Single link: TEST."""
    cfg = _cfg(
        InterfaceType.TEST,
        "/dev/pts/1",
        InterfaceType.TEST,
        "/dev/pts/1",
    )
    argv = build_middleware_argv(cfg, FAKE_BINARY)
    assert argv[1] == "TEST"
    assert argv[2] == "/dev/pts/1"
    assert argv[3] == "TEST"
    assert argv[4] == "/dev/pts/1"
    assert len(argv) == 7


def test_build_middleware_argv_gse_av_test_uart_e5():
    """Single link: TEST_UART_E5."""
    cfg = _cfg(
        InterfaceType.TEST_UART_E5,
        "/dev/pts/2",
        InterfaceType.TEST_UART_E5,
        "/dev/pts/2",
    )
    argv = build_middleware_argv(cfg, FAKE_BINARY)
    assert argv[1] == "TEST_UART_E5"
    assert argv[2] == "/dev/pts/2"
    assert argv[3] == "TEST_UART_E5"
    assert argv[4] == "/dev/pts/2"
    assert len(argv) == 7


def test_build_middleware_argv_uart_e5_requires_lora_config():
    cfg = _cfg(
        InterfaceType.UART_E5,
        "/dev/serial0",
        InterfaceType.UART_E5,
        "/dev/serial0",
        lora_config=None,
    )
    with pytest.raises(
        ValueError, match="UART_E5 interface requires lora_config"
    ):
        build_middleware_argv(cfg, FAKE_BINARY)


def test_build_middleware_argv_uart_e5_with_lora():
    cfg = _cfg(
        InterfaceType.UART_E5,
        "/dev/serial0",
        InterfaceType.UART_E5,
        "/dev/serial0",
        lora_config=LORA_CONFIG,
    )
    argv = build_middleware_argv(cfg, FAKE_BINARY)
    assert argv[0] == FAKE_BINARY
    assert argv[1] == "UART_E5"
    assert argv[2] == "/dev/serial0"
    assert argv[3] == "UART_E5"
    assert argv[4] == "/dev/serial0"
    assert argv[5] == PENDANT
    assert argv[6] == WEB
    assert argv[7] == LORA_CONFIG["frequency"]
    assert argv[15] == LORA_CONFIG["net"]
    assert len(argv) == 16


def test_build_middleware_argv_opt_arg_gse_only():
    cfg = _cfg(
        InterfaceType.TCP,
        "127.0.0.1:9000",
        InterfaceType.TCP,
        "127.0.0.1:9000",
        opt_arg="--GSE_ONLY",
    )
    argv = build_middleware_argv(cfg, FAKE_BINARY)
    assert argv[-1] == "--GSE_ONLY"
    assert len(argv) == 8


def test_build_middleware_argv_uart_e5_plus_opt_arg():
    cfg = _cfg(
        InterfaceType.UART_E5,
        "/dev/serial0",
        InterfaceType.UART_E5,
        "/dev/serial0",
        opt_arg="--GSE_ONLY",
        lora_config=LORA_CONFIG,
    )
    argv = build_middleware_argv(cfg, FAKE_BINARY)
    assert argv[-1] == "--GSE_ONLY"
    assert len(argv) == 17


def test_build_middleware_argv_ordering():
    """Order: binary, gse_type, gse_path, av_type, av_path, pendant, web, [lora], [opt]."""
    cfg = MiddlewareConfig(
        release=True,
        interface_gse_type=InterfaceType.TEST,
        device_path_gse="/dev/pty/0",
        interface_av_type=InterfaceType.TEST,
        device_path_av="/dev/pty/0",
        pendant_socket_path="pendant_sock",
        web_control_socket_path="web_sock",
        opt_arg="--GSE_ONLY",
        lora_config=None,
    )
    argv = build_middleware_argv(cfg, FAKE_BINARY)
    assert argv == [
        FAKE_BINARY,
        "TEST",
        "/dev/pty/0",
        "TEST",
        "/dev/pty/0",
        "pendant_sock",
        "web_sock",
        "--GSE_ONLY",
    ]


def test_build_middleware_argv_rejects_non_interface_type():
    bad_cfg = MiddlewareConfig(
        release=False,
        interface_gse_type="TCP",  # type: ignore[arg-type]
        device_path_gse="/dev/null",
        interface_av_type=InterfaceType.TCP,
        device_path_av="/dev/null",
        pendant_socket_path=PENDANT,
        web_control_socket_path=WEB,
    )
    with pytest.raises(ValueError, match="must be InterfaceType"):
        build_middleware_argv(bad_cfg, FAKE_BINARY)
