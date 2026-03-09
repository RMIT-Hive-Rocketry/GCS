#include "interface_factory.hpp"

#include <stdexcept>

#include "tcp_interface.hpp"
#include "test_interface.hpp"
#include "test_uart_interface.hpp"
#include "uart_interface.hpp"

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
  const std::string ip = endpoint.substr(0, colon);
  const std::string port_str = endpoint.substr(colon + 1);
  if (ip.empty() || port_str.empty()) {
    throw std::runtime_error(
        "TCP interface requires non-empty IP and port. Pass --tcp-ip and "
        "--tcp-port from rocket.py.");
  }
  const unsigned long port_val = std::stoul(port_str);
  if (port_val > 65535) {
    throw std::runtime_error("TCP port must be in range 1-65535");
  }
  return {ip, static_cast<uint16_t>(port_val)};
}

}  // namespace

std::shared_ptr<RadioInterface> create_interface(
    const std::string& INTERFACE_NAME, const std::string& DEVICE_PATH,
    const LoraConfig& lora_cfg) {
  std::shared_ptr<RadioInterface> interface;

  if (INTERFACE_NAME == "UART") {
    interface = std::make_shared<UartInterface>(lora_cfg, DEVICE_PATH);
  } else if (INTERFACE_NAME == "TEST") {
    interface = std::make_shared<TestInterface>(DEVICE_PATH);
  } else if (INTERFACE_NAME == "TEST_UART") {
    interface = std::make_shared<TestUartInterface>(DEVICE_PATH);
  } else if (INTERFACE_NAME == "TCP") {
    const auto [ip, port] = parse_tcp_endpoint(DEVICE_PATH);
    interface = std::make_shared<TcpInterface>(ip, port);
  } else {
    throw std::runtime_error("Error: Invalid interface type");
  }

  return interface;
}
