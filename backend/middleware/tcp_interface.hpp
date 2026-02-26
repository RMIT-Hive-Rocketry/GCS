// tcp_interface.hpp
#pragma once

#include <netinet/in.h>

#include <mutex>
#include <string>
#include <vector>

#include "radio_interface.hpp"

class TcpInterface : public RadioInterface {
 public:
  // If ENDPOINT is non-empty, it may be of the form "ip" or "ip:port".
  // Otherwise a built-in static IP/port is used.
  explicit TcpInterface(const std::string& endpoint = "127.0.0.1",
                        uint16_t port = 5000);
  ~TcpInterface() override;

  bool initialize() override;
  ssize_t read_data(std::vector<uint8_t>& buffer) override;
  ssize_t write_data(const std::vector<uint8_t>& data) override;

 private:
  std::recursive_mutex io_mutex_;

  std::string ip_;
  uint16_t port_;
  int sock_fd_ = -1;

  sockaddr_in remote_addr_{};
};
