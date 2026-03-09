#pragma once

#include <memory>
#include <string>

#include "radio_interface.hpp"
#include "uart_interface.hpp"  // for LoraConfig

/// Builds a RadioInterface from interface type name and device path.
/// Used by the middleware server and by tests.
/// @param INTERFACE_NAME One of "UART", "TEST", "TEST_UART", "TCP"
/// @param DEVICE_PATH Device path or endpoint (e.g. /dev/serial0, /dev/pts/X, ip:port)
/// @param lora_cfg Required for UART; ignored for other types
/// @return Shared pointer to the concrete interface
/// @throws std::runtime_error if INTERFACE_NAME is invalid
std::shared_ptr<RadioInterface> create_interface(
    const std::string& INTERFACE_NAME,
    const std::string& DEVICE_PATH,
    const LoraConfig& lora_cfg = {});
