// uart_e5_interface.hpp
#pragma once

#include <termios.h>

#include <chrono>
#include <mutex>
#include <string>
#include <vector>

#include "radio_interface.hpp"

struct LoraConfig {
  std::string frequency;
  std::string spread_factor;
  std::string bandwidth;
  std::string tx_preamble;
  std::string rx_preamble;
  std::string power;
  std::string crc;
  std::string iq;
  std::string net;
};

class UartE5Interface : public RadioInterface {
 public:
  UartE5Interface(
      LoraConfig lora_cfg, const std::string& device_path = "/dev/serial0",
      int baud_rate = B230400);  // Default to RPi ttyAMA0 and 230400 baud
  virtual ~UartE5Interface();

  bool initialize() override;
  ssize_t read_data(std::vector<uint8_t>& buffer) override;
  ssize_t write_data(const std::vector<uint8_t>& data) override;
  static std::vector<uint8_t> hex_string_to_bytes(const std::string& hex);

 private:
  std::recursive_mutex io_mutex_;
  int baud_rate_;
  int uart_fd_ = -1;
  std::string device_path_;
  std::string response_buffer_;
  LoraConfig lora_cfg_;

  constexpr static int AT_TIMEOUT_MS = 1000;

  // Enums to track if you need to override continuous modes
  enum ModemContinuousState {
    NOT_CONTINUOUS,
    TXCW,     // Not currently used
    TXCLORA,  // Not currently used
    RXLRPKT,  // Basic RX
  };
  // Keep track if you're currently in a continuous mode
  ModemContinuousState current_modem_state_;

  bool at_send_command(
      const std::string& command, const std::string& expected_response,
      const int timeout_ms = AT_TIMEOUT_MS,
      const ModemContinuousState = ModemContinuousState::NOT_CONTINUOUS);
  void configure_uart();
  void at_setup();
  // https://files.seeedstudio.com/products/317990687/res/LoRa-E5+AT+Command+Specification_V1.0+.pdf#page=52

  ssize_t write_serial(const std::vector<uint8_t>& data);
  std::vector<uint8_t> read_with_timeout(int timeout_ms);
};
