#include "interface_factory.hpp"

#include <iostream>
#include <stdexcept>

#include "tcp_interface.hpp"
#include "test_interface.hpp"
#include "test_uart_e5_interface.hpp"
#include "uart_e5_interface.hpp"

namespace {

std::pair<std::string, uint16_t> parse_tcp_endpoint(
    const std::string& endpoint) {
  const size_t colon = endpoint.find(':');
  if (colon == std::string::npos || colon == 0 ||
      colon == endpoint.size() - 1) {
    throw std::runtime_error(
        "TCP interface requires device path in the form ip:port (e.g. "
        "192.168.0.150:5000). Pass --tcp-ip and --tcp-port from rocket.py.");
  }

  const std::string ip_str = endpoint.substr(0, colon);
  const std::string port_str = endpoint.substr(colon + 1);

  struct sockaddr_in sa;
  // inet_pton returns 1 on success, 0 for invalid format, -1 for system errors
  if (inet_pton(AF_INET, ip_str.c_str(), &(sa.sin_addr)) != 1) {
    throw std::runtime_error("Invalid IPv4 address: " + ip_str);
  }

  const unsigned long port_val = [port_str]() {
    try {
      unsigned long v = std::stoul(port_str);
      if (v > 65535) throw std::out_of_range("Port out of 16-bit range");
      return v;
    } catch (const std::exception& e) {
      throw std::runtime_error("Invalid port '" + port_str + "': " + e.what());
    }
  }();

  return {ip_str, static_cast<uint16_t>(port_val)};
}

}  // namespace

std::shared_ptr<RadioInterface> create_interface(
    const std::string& INTERFACE_NAME, const std::string& DEVICE_PATH,
    const LoraConfig& lora_cfg) {
  std::shared_ptr<RadioInterface> interface;

  if (!is_valid_interface_type(INTERFACE_NAME)) {
    throw std::invalid_argument(INTERFACE_NAME + " is an invalid interface");
  }

  if (INTERFACE_NAME == "UART_E5") {
    interface = std::make_shared<UartE5Interface>(lora_cfg, DEVICE_PATH);
  } else if (INTERFACE_NAME == "TEST") {
    interface = std::make_shared<TestInterface>(DEVICE_PATH);
  } else if (INTERFACE_NAME == "TEST_UART_E5") {
    interface = std::make_shared<TestUartE5Interface>(DEVICE_PATH);
  } else if (INTERFACE_NAME == "TCP") {
    const auto [ip, port] = parse_tcp_endpoint(DEVICE_PATH);
    interface = std::make_shared<TcpInterface>(ip, port);
  } else {
    throw std::runtime_error("Error: Invalid interface type");
  }

  return interface;
}

bool is_valid_interface_type(const std::string& name) {
  return name == "UART_E5" || name == "TEST" || name == "TEST_UART_E5" ||
         name == "TCP";
}
