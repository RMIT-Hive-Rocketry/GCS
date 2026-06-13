// uart_feather_interface.hpp
#pragma once

#include <termios.h>

#include <deque>
#include <mutex>
#include <string>
#include <vector>

#include "radio_interface.hpp"
#include "uart_e5_interface.hpp"  // for LoraConfig

/// Adafruit Feather 32u4 RFM9x (433 MHz) running the AT-style LoRa bridge
/// firmware. Appears as a USB CDC serial port: newline-terminated ASCII
/// commands, every response ends with "OK" or "ERROR: <reason>". Received
/// LoRa packets are pushed asynchronously as "+RECV: <rssi>,<snr>,<hex>"
/// lines which can interleave with command responses.
///
/// WARNING: never open this port at 1200 baud. A 1200-baud open/close resets
/// the 32u4 into its bootloader (that is the firmware-flashing mechanism).
/// The onboard LED (pin 13) is on for 1 s at power-up and again when the host
/// sends AT+BLINK during init; it stays on for the duration of each LoRa TX.
class UartFeatherInterface : public RadioInterface {
 public:
  /// Only lora_cfg.frequency (MHz, 410-525) and lora_cfg.power (dBm, 2-20)
  /// are used; the other modem settings are fixed by the firmware
  /// (RadioHead defaults: 125 kHz BW, CR 4/5, SF7).
  UartFeatherInterface(LoraConfig lora_cfg, const std::string& device_path,
                       int baud_rate = B115200);
  virtual ~UartFeatherInterface();

  bool initialize() override;
  ssize_t read_data(std::vector<uint8_t>& buffer) override;
  ssize_t write_data(const std::vector<uint8_t>& data) override;

 private:
  std::recursive_mutex io_mutex_;
  int baud_rate_;
  int uart_fd_ = -1;
  std::string device_path_;
  std::string line_buffer_;
  // Decoded +RECV payloads (RSSI/SNR floats inserted, same layout as
  // UartE5Interface) buffered until the next read_data call
  std::deque<std::vector<uint8_t>> rx_packets_;
  LoraConfig lora_cfg_;

  constexpr static int AT_TIMEOUT_MS = 1000;
  // AT+BLINK holds the LED on for 1 s before replying OK
  constexpr static int BLINK_TIMEOUT_MS = 2000;
  // AT+SENDX blocks until TX completes, which can take hundreds of ms
  constexpr static int SEND_TIMEOUT_MS = 5000;
  constexpr static size_t MAX_PAYLOAD_BYTES = 251;  // RH_RF95_MAX_MESSAGE_LEN

  void configure_uart();
  void at_setup();
  /// Send one command and wait for its OK/ERROR terminator. "+..." data
  /// lines seen before the terminator are appended to data_lines (if given);
  /// "+RECV:" lines are routed to rx_packets_ instead.
  bool at_send_command(const std::string& command,
                       std::vector<std::string>* data_lines = nullptr,
                       int timeout_ms = AT_TIMEOUT_MS);
  /// Read serial for up to timeout_ms and split into complete lines.
  /// "+RECV:" lines are decoded into rx_packets_; everything else is
  /// appended to response_lines.
  void poll_lines(int timeout_ms, std::vector<std::string>& response_lines);
  void handle_recv_line(const std::string& line);
  ssize_t write_serial(const std::vector<uint8_t>& data);
};
