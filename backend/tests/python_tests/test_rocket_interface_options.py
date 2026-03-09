"""Unit tests for rocket.py interface option validation (_validate_interface_options)."""

import pytest
import click

from rocket import _validate_interface_options


def test_validate_interface_options_valid_single():
    """Single interface set, av/gse both None is valid."""
    _validate_interface_options("UART", None, None)
    _validate_interface_options("TCP", None, None)


def test_validate_interface_options_valid_dual():
    """Both interface_av and interface_gse set, interface None is valid."""
    _validate_interface_options(None, "TCP", "UART")
    _validate_interface_options(None, "UART", "TCP")
    _validate_interface_options(None, "TEST", "TEST_UART")


def test_validate_interface_options_valid_all_none():
    """All None means use config (single interface from config)."""
    _validate_interface_options(None, None, None)


def test_validate_interface_options_invalid_single_and_av():
    """Cannot specify both --interface and --interface-av."""
    with pytest.raises(click.UsageError) as exc_info:
        _validate_interface_options("UART", "TCP", None)
    assert "Do not specify both" in str(exc_info.value)
    assert "interface-av" in str(exc_info.value).lower() or "interface" in str(exc_info.value).lower()


def test_validate_interface_options_invalid_single_and_gse():
    """Cannot specify both --interface and --interface-gse."""
    with pytest.raises(click.UsageError) as exc_info:
        _validate_interface_options("TCP", None, "UART")
    assert "Do not specify both" in str(exc_info.value)


def test_validate_interface_options_invalid_only_av():
    """Only --interface-av without --interface-gse is invalid."""
    with pytest.raises(click.UsageError) as exc_info:
        _validate_interface_options(None, "TCP", None)
    assert "both" in str(exc_info.value).lower()
    assert "interface-av" in str(exc_info.value).lower() or "interface-gse" in str(exc_info.value).lower()


def test_validate_interface_options_invalid_only_gse():
    """Only --interface-gse without --interface-av is invalid."""
    with pytest.raises(click.UsageError) as exc_info:
        _validate_interface_options(None, None, "UART")
    assert "both" in str(exc_info.value).lower()


def test_validate_interface_options_invalid_all_three():
    """interface and both av/gse is invalid (single + dual)."""
    with pytest.raises(click.UsageError) as exc_info:
        _validate_interface_options("TEST", "TCP", "UART")
    assert "Do not specify both" in str(exc_info.value)
