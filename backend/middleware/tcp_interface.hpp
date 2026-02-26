// tcp_interface.hpp
#pragma once

#include <netinet/in.h>

#include <mutex>
#include <string>
#include <vector>

#include "lora_interface.hpp"

// Simple LoRa interface implementation that forwards bytes over a TCP socket.
// Opens a blocking TCP connection to a static IP/port and uses TCP_NODELAY.
class TcpInterface : public LoraInterface {
 public:
  // If ENDPOINT is non-empty, it may be of the form "ip" or "ip:port".
  // Otherwise a built-in static IP/port is used.
  explicit TcpInterface(const std::string &endpoint = "");
  ~TcpInterface() override;

  bool initialize() override;
  ssize_t read_data(std::vector<uint8_t> &buffer) override;
  ssize_t write_data(const std::vector<uint8_t> &data) override;

 private:
  std::recursive_mutex io_mutex_;

  std::string ip_;
  uint16_t port_;
  int sock_fd_ = -1;

  sockaddr_in remote_addr_{};

  void parse_endpoint(const std::string &endpoint);
};

