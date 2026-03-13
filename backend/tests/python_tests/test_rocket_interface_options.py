"""Unit tests for rocket.py interface option validation (_validate_interface_options)."""

import pytest
import click

from rocket import _validate_interface_options


def test_validate_interface_options_valid_single():
    """Single interface set, av/gse both None is valid."""
    _validate_interface_options("UART_E5", None, None)
    _validate_interface_options("TCP", None, None)


def test_validate_interface_options_valid_dual():
    """Both interface_av and interface_gse set, interface None is valid."""
    _validate_interface_options(None, "TCP", "UART_E5")
    _validate_interface_options(None, "UART_E5", "TCP")
    with pytest.raises(NotImplementedError):
        _validate_interface_options(None, "TEST", "TEST_UART_E5")
    with pytest.raises(NotImplementedError):
        _validate_interface_options(None, "TEST", "TCP")
    with pytest.raises(NotImplementedError):
        _validate_interface_options(None, "TCP", "TEST")


def test_validate_interface_options_valid_all_none():
    """All None means use config (single interface from config)."""
    _validate_interface_options(None, None, None)


def test_validate_interface_options_invalid_single_and_av():
    """Cannot specify both --interface and --interface-av."""
    with pytest.raises(click.UsageError) as exc_info:
        _validate_interface_options("UART_E5", "TCP", None)
    assert "Do not specify both" in str(exc_info.value)
    assert (
        "interface-av" in str(exc_info.value).lower()
        or "interface" in str(exc_info.value).lower()
    )


def test_validate_interface_options_invalid_single_and_gse():
    """Cannot specify both --interface and --interface-gse."""
    with pytest.raises(click.UsageError) as exc_info:
        _validate_interface_options("TCP", None, "UART_E5")
    assert "Do not specify both" in str(exc_info.value)


def test_validate_interface_options_invalid_only_av():
    """Only --interface-av without --interface-gse is invalid."""
    with pytest.raises(click.UsageError) as exc_info:
        _validate_interface_options(None, "TCP", None)
    assert "both" in str(exc_info.value).lower()
    assert (
        "interface-av" in str(exc_info.value).lower()
        or "interface-gse" in str(exc_info.value).lower()
    )


def test_validate_interface_options_invalid_only_gse():
    """Only --interface-gse without --interface-av is invalid."""
    with pytest.raises(click.UsageError) as exc_info:
        _validate_interface_options(None, None, "UART_E5")
    assert "both" in str(exc_info.value).lower()


def test_validate_interface_options_invalid_all_three():
    """interface and both av/gse is invalid (single + dual)."""
    with pytest.raises(click.UsageError) as exc_info:
        _validate_interface_options("TEST", "TCP", "UART_E5")
    assert "Do not specify both" in str(exc_info.value)
