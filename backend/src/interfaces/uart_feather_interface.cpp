// uart_feather_interface.cpp
#include "uart_feather_interface.hpp"

#include <fcntl.h>
#include <sys/select.h>
#include <termios.h>
#include <unistd.h>

#include <algorithm>
#include <chrono>
#include <cstring>
#include <iomanip>
#include <sstream>
#include <system_error>

#include "subprocess_logging.hpp"

namespace {

std::string bytes_to_hex(const std::vector<uint8_t>& data) {
  std::ostringstream oss;
  oss << std::hex << std::uppercase << std::setfill('0');
  for (uint8_t byte : data) {
    oss << std::setw(2) << static_cast<int>(byte);
  }
  return oss.str();
}

}  // namespace

UartFeatherInterface::UartFeatherInterface(LoraConfig lora_cfg,
                                           const std::string& device_path,
                                           int baud_rate)
    : RadioInterface(DuplexMode::HALF_DUPLEX),
      baud_rate_(baud_rate),
      device_path_(device_path),
      lora_cfg_(lora_cfg) {}

UartFeatherInterface::~UartFeatherInterface() {
  std::lock_guard<std::recursive_mutex> lock(io_mutex_);
  // If file descriptor indicates it is open, close it
  if (uart_fd_ >= 0) close(uart_fd_);
}

bool UartFeatherInterface::initialize() {
  std::lock_guard<std::recursive_mutex> lock(io_mutex_);
  uart_fd_ =
      open(device_path_.c_str(), O_RDWR | O_NOCTTY | O_SYNC | O_NONBLOCK);
  if (uart_fd_ < 0) {
    slogger::error("Failed to open Feather device: " + device_path_);
    slogger::warning(
        "The UART_FEATHER interface requires the Adafruit Feather 32u4 RFM9x "
        "to be plugged in (USB VID:PID 239a:800c).");
    throw std::system_error(errno, std::system_category(),
                            "Failed to open UART device");
  }

  configure_uart();
  at_setup();
  return true;
}

void UartFeatherInterface::configure_uart() {
  struct termios tty;
  if (tcgetattr(uart_fd_, &tty) != 0) {
    throw std::system_error(errno, std::system_category(), "tcgetattr failed");
  }

  // Never set 1200 baud here: a 1200-baud open resets the 32u4 into its
  // bootloader. The CDC port ignores the actual rate, 115200 is safe.
  cfsetospeed(&tty, baud_rate_);
  cfsetispeed(&tty, baud_rate_);

  // 8N1 configuration
  tty.c_cflag &= ~PARENB;  // No parity
  tty.c_cflag &= ~CSTOPB;  // 1 stop bit
  tty.c_cflag &= ~CSIZE;
  tty.c_cflag |= CS8;     // 8 data bits
  tty.c_cflag |= CREAD;   // Enable receiver
  tty.c_cflag |= CLOCAL;  // Ignore modem controls

  // Raw input/output
  tty.c_lflag &= ~(ICANON | ECHO | ECHOE | ISIG);
  tty.c_iflag &= ~(IXON | IXOFF | IXANY | IGNBRK | BRKINT | PARMRK | ISTRIP |
                   INLCR | IGNCR | ICRNL);
  tty.c_oflag &= ~OPOST;

  // Timeout configuration (0.5s)
  tty.c_cc[VMIN] = 0;
  tty.c_cc[VTIME] = 5;

  if (tcsetattr(uart_fd_, TCSANOW, &tty) != 0) {
    throw std::system_error(errno, std::system_category(), "tcsetattr failed");
  }
}

void UartFeatherInterface::at_setup() {
  slogger::info("Connecting to Feather LoRa bridge...");

  // The line buffer may hold stale bytes right after opening, so retry the
  // ping a few times before giving up
  bool module_found = false;
  for (int attempt = 0; attempt < 3 && !module_found; attempt++) {
    module_found = at_send_command("AT", nullptr, 500);
  }
  if (!module_found) {
    slogger::error("No Feather AT bridge found on " + device_path_);
    throw std::runtime_error("Feather LoRa bridge not responding to AT");
  }

  // Confirm the radio silicon itself is alive (SX127x version register)
  std::vector<std::string> ver_lines;
  if (at_send_command("AT+VER?", &ver_lines) && !ver_lines.empty() &&
      ver_lines.front().find("0x12") != std::string::npos) {
    slogger::info("Feather radio alive (SX127x version 0x12)");
  } else {
    slogger::warning("Feather radio version check failed");
  }

  if (!at_send_command("AT+FREQ=" + lora_cfg_.frequency)) {
    slogger::error("Failed to set Feather frequency: " + lora_cfg_.frequency);
  }
  if (!at_send_command("AT+POWER=" + lora_cfg_.power)) {
    slogger::error("Failed to set Feather TX power: " + lora_cfg_.power);
  }

  slogger::info("End of Feather setup...");
}

void UartFeatherInterface::poll_lines(
    int timeout_ms, std::vector<std::string>& response_lines) {
  fd_set set;
  timeval timeout{};

  FD_ZERO(&set);
  FD_SET(uart_fd_, &set);

  timeout.tv_sec = timeout_ms / 1000;
  timeout.tv_usec = (timeout_ms % 1000) * 1000;

  while (true) {
    int result = select(uart_fd_ + 1, &set, nullptr, nullptr, &timeout);
    if (result <= 0) break;

    char chunk[128];
    ssize_t n = read(uart_fd_, chunk, sizeof(chunk));
    if (n <= 0) break;
    line_buffer_.append(chunk, n);

    // Continue reading while data is immediately available
    timeout.tv_sec = 0;
    timeout.tv_usec = 10000;  // 10ms subsequent timeout
  }

  // Demultiplex complete lines: async "+RECV:" packets vs command responses
  size_t line_end;
  while ((line_end = line_buffer_.find('\n')) != std::string::npos) {
    std::string line = line_buffer_.substr(0, line_end);
    line_buffer_.erase(0, line_end + 1);
    line.erase(std::remove(line.begin(), line.end(), '\r'), line.end());
    if (line.empty()) continue;

    if (line.rfind("+RECV:", 0) == 0) {
      handle_recv_line(line);
    } else {
      response_lines.push_back(line);
    }
  }
}

void UartFeatherInterface::handle_recv_line(const std::string& line) {
  // Format: +RECV: <rssi>,<snr>,<hex payload>
  try {
    const std::string body = line.substr(std::strlen("+RECV:"));
    const size_t comma1 = body.find(',');
    const size_t comma2 = body.find(',', comma1 + 1);
    if (comma1 == std::string::npos || comma2 == std::string::npos) {
      throw std::runtime_error("malformed +RECV line");
    }

    const int rssi = std::stoi(body.substr(0, comma1));
    const int snr = std::stoi(body.substr(comma1 + 1, comma2 - comma1 - 1));
    std::vector<uint8_t> payload =
        UartE5Interface::hex_string_to_bytes(body.substr(comma2 + 1));

    if (payload.empty()) {
      slogger::warning("Empty payload, skipping metrics insertion");
      return;
    }

    // Insert RSSI/SNR after the 1-byte packet ID, same layout as UartE5
    auto rssi_bytes = float_to_be_bytes(static_cast<float>(rssi));
    auto snr_bytes = float_to_be_bytes(static_cast<float>(snr));
    payload.insert(payload.begin() + 1, rssi_bytes.begin(), rssi_bytes.end());
    payload.insert(payload.begin() + 5,  // 1 + 4 bytes
                   snr_bytes.begin(), snr_bytes.end());

    rx_packets_.push_back(std::move(payload));
  } catch (const std::exception& e) {
    slogger::error("Failed to parse +RECV line: " + std::string(e.what()));
  }
}

ssize_t UartFeatherInterface::write_serial(const std::vector<uint8_t>& data) {
  if (uart_fd_ < 0) return -1;

  ssize_t written = write(uart_fd_, data.data(), data.size());
  if (written < 0) {
    slogger::error("Failed to write to serial port");
    throw std::system_error(errno, std::system_category(),
                            "Serial write failed");
  }
  return written;
}

bool UartFeatherInterface::at_send_command(const std::string& command,
                                           std::vector<std::string>* data_lines,
                                           const int timeout_ms) {
  std::lock_guard<std::recursive_mutex> lock(io_mutex_);

  std::string full_command = command + "\n";
  slogger::debug("Sending AT command: " + command);
  std::vector<uint8_t> cmd_data(full_command.begin(), full_command.end());

  if (write_serial(cmd_data) != static_cast<ssize_t>(cmd_data.size())) {
    slogger::error("Failed to send AT command: " + command);
    return false;
  }

  auto start = std::chrono::steady_clock::now();
  while (std::chrono::duration_cast<std::chrono::milliseconds>(
             std::chrono::steady_clock::now() - start)
             .count() < timeout_ms) {
    std::vector<std::string> lines;
    poll_lines(50, lines);

    for (const std::string& line : lines) {
      if (line == "OK") {
        slogger::debug("AT command successful: " + command);
        return true;
      }
      if (line.rfind("ERROR", 0) == 0) {
        slogger::error("AT command '" + command + "' failed: " + line);
        return false;
      }
      if (data_lines != nullptr) data_lines->push_back(line);
    }
  }

  slogger::warning("AT command timed out: " + command);
  return false;
}

/// @brief Pop one buffered received LoRa payload (if any)
/// @param buffer
/// @return Returns amount of bytes read. 0 if no packet pending, -1 if failed
ssize_t UartFeatherInterface::read_data(std::vector<uint8_t>& buffer) {
  std::lock_guard<std::recursive_mutex> lock(io_mutex_);
  if (uart_fd_ < 0) {
    slogger::error("Feather file descriptor is invalid");
    return -1;
  }

  // The radio idles in receive mode, no command needed; just poll the port
  std::vector<std::string> stray_lines;
  poll_lines(100, stray_lines);
  for (const std::string& line : stray_lines) {
    slogger::debug("Unexpected line outside a command: " + line);
  }

  if (rx_packets_.empty()) return 0;

  std::vector<uint8_t> payload = std::move(rx_packets_.front());
  rx_packets_.pop_front();

  if (buffer.size() < payload.size()) {
    buffer.resize(payload.size());
  }
  std::copy(payload.begin(), payload.end(), buffer.begin());
  return payload.size();
}

/// @brief Write serial data to the LoRa band through the Feather bridge
/// @param data Binary data bytes
/// @return Amount of bytes transmitted, -1 on failure
ssize_t UartFeatherInterface::write_data(const std::vector<uint8_t>& data) {
  std::lock_guard<std::recursive_mutex> lock(io_mutex_);
  if (uart_fd_ < 0) {
    slogger::error("Feather device unavailable for write");
    return -1;
  }
  if (data.empty() || data.size() > MAX_PAYLOAD_BYTES) {
    slogger::error("Feather payload must be 1-" +
                   std::to_string(MAX_PAYLOAD_BYTES) + " bytes, got " +
                   std::to_string(data.size()));
    return -1;
  }

  // Hex-encoded send so arbitrary binary bytes are safe
  const std::string command = "AT+SENDX=" + bytes_to_hex(data);
  if (at_send_command(command, nullptr, SEND_TIMEOUT_MS)) {
    return data.size();
  }
  slogger::error("LoRa transmission failed");
  return -1;
}
