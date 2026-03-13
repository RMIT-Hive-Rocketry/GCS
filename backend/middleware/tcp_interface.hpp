// tcp_interface.hpp
#pragma once

#include <netinet/in.h>

#include <chrono>
#include <mutex>
#include <string>
#include <vector>

#include "middleware_timing.hpp"
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
  enum class ConnectionState { CONNECTED, DISCONNECTED_RETRYING };

  bool connect_socket_locked_();
  bool ensure_connected_or_retry_locked_();
  void mark_disconnected_locked_(const std::string& reason);
  void close_socket_locked_();

  std::recursive_mutex io_mutex_;

  std::string ip_;
  uint16_t port_;
  int sock_fd_ = -1;
  ConnectionState connection_state_ = ConnectionState::DISCONNECTED_RETRYING;
  std::chrono::steady_clock::time_point next_retry_time_ =
      std::chrono::steady_clock::now();

  std::chrono::milliseconds retry_backoff_{
      middleware_timing::initial_tcp_retry_backoff};

  sockaddr_in remote_addr_{};
};
