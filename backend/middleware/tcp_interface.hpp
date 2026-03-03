// tcp_interface.hpp
#pragma once

#include <netinet/in.h>

#include <mutex>
#include <string>
#include <vector>

#include "radio_interface.hpp"

class TcpInterface : public RadioInterface {
 public:
  // IP and port are required (no defaults). Must be passed from the process
  // that launches the middleware (e.g. rocket.py) via command line.
  explicit TcpInterface(const std::string& ip, uint16_t port);
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
