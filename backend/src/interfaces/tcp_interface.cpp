// tcp_interface.cpp
#include "tcp_interface.hpp"

#include <arpa/inet.h>
#include <fcntl.h>
#include <netinet/tcp.h>
#include <sys/socket.h>
#include <unistd.h>

#include <algorithm>
#include <chrono>
#include <cstring>
#include <stdexcept>
#include <system_error>
#include <thread>

#include "debug_functions.hpp"
#include "subprocess_logging.hpp"

TcpInterface::TcpInterface(const std::string& ip, uint16_t port)
    : RadioInterface(DuplexMode::FULL_DUPLEX), ip_(ip), port_(port) {}

TcpInterface::~TcpInterface() {
  std::lock_guard<std::recursive_mutex> lock(io_mutex_);
  close_socket_locked_();
}

bool TcpInterface::initialize() {
  std::lock_guard<std::recursive_mutex> lock(io_mutex_);

  if (ip_.empty()) {
    throw std::runtime_error(
        "TCP interface requires IP and port to be passed from the command line "
        "(e.g. from rocket.py). No default is allowed.");
  }

  // Disable Nagle's algorithm for low-latency sends. Spam that shit
  // See https://redisgate.kr/images/server/tcp_nodelay.png
  int flag = 1;
  if (setsockopt(sock_fd_, IPPROTO_TCP, TCP_NODELAY, &flag, sizeof(flag)) < 0) {
    slogger::error("Failed to set TCP_NODELAY on socket");
  }

  std::memset(&remote_addr_, 0, sizeof(remote_addr_));
  remote_addr_.sin_family = AF_INET;
  remote_addr_.sin_port = htons(port_);
  if (inet_pton(AF_INET, ip_.c_str(), &remote_addr_.sin_addr) <= 0) {
    throw std::runtime_error("Invalid TCP interface IP address: " + ip_);
  }

  return connect_socket_locked_();
}

// NOTE we are not using OML or anything. Raw TCP bytes only
ssize_t TcpInterface::write_data(const std::vector<uint8_t>& data) {
  std::lock_guard<std::recursive_mutex> lock(io_mutex_);
  if (!ensure_connected_or_retry_locked_()) {
    return -1;
  }

  // For heartbeat traffic, suppress duplicate payloads sent too recently.
  auto now = std::chrono::steady_clock::now();
  bool is_duplicate_payload = (data == last_payload_);
  bool within_heartbeat_window =
      (now - last_send_time_) < middleware_timing::TCP_HEARTBEAT;
  if (is_duplicate_payload && within_heartbeat_window) {
    return static_cast<ssize_t>(data.size());
  }

  const uint8_t* buf = data.data();
  size_t total = 0;
  while (total < data.size()) {
    std::string hex_output =
        debug::vectorToHexString(data, static_cast<ssize_t>(data.size()));
    slogger::debug("Sending data (Hex): " + hex_output);
    ssize_t n = ::send(sock_fd_, buf + total, data.size() - total, 0);
    if (n < 0) {
      if (errno == EINTR) continue;
      mark_disconnected_locked_("TCP send failed: " +
                                std::string(std::strerror(errno)));
      return -1;
    }
    if (n == 0) break;
    total += static_cast<size_t>(n);
  }

  if (total == data.size()) {
    last_payload_ = data;
    last_send_time_ = now;
  }

  return static_cast<ssize_t>(total);
}

ssize_t TcpInterface::read_data(std::vector<uint8_t>& buffer) {
  std::lock_guard<std::recursive_mutex> lock(io_mutex_);
  if (buffer.empty()) {
    return 0;
  }
  if (!ensure_connected_or_retry_locked_()) {
    return 0;
  }

  // Blocking read with timeout
  fd_set read_fds;
  FD_ZERO(&read_fds);
  FD_SET(sock_fd_, &read_fds);

  timeval timeout{};
  timeout.tv_sec = 0;
  timeout.tv_usec = 100000;  // 100ms

  int ready = ::select(sock_fd_ + 1, &read_fds, nullptr, nullptr, &timeout);
  if (ready < 0) {
    if (errno == EINTR) return 0;
    mark_disconnected_locked_("TCP select failed: " +
                              std::string(std::strerror(errno)));
    return 0;
  }
  if (ready == 0) {
    // Timeout, no data.
    return 0;
  }

  ssize_t n =
      ::recv(sock_fd_, buffer.data(), static_cast<int>(buffer.size()), 0);
  if (n < 0) {
    if (errno == EINTR) {
      return 0;
    }
    mark_disconnected_locked_("TCP recv failed: " +
                              std::string(std::strerror(errno)));
    return 0;
  }
  if (n == 0) {
    mark_disconnected_locked_("TCP peer closed connection");
    return 0;
  }

  return n;
}

bool TcpInterface::connect_socket_locked_() {
  close_socket_locked_();
  connection_state_ = ConnectionState::DISCONNECTED_RETRYING;

  sock_fd_ = ::socket(AF_INET, SOCK_STREAM, 0);
  if (sock_fd_ < 0) {
    mark_disconnected_locked_("Failed to create TCP socket: " +
                              std::string(std::strerror(errno)));
    return false;
  }

  // Set NODELAY again. See initialisation for more comments
  int flag = 1;
  if (setsockopt(sock_fd_, IPPROTO_TCP, TCP_NODELAY, &flag, sizeof(flag)) < 0) {
    slogger::warning("Failed to set TCP_NODELAY on socket");
  }

  slogger::warning("(TCP SIGNAL LOST)");

  if (::connect(sock_fd_, reinterpret_cast<sockaddr*>(&remote_addr_),
                sizeof(remote_addr_)) < 0) {
    mark_disconnected_locked_("Failed to connect TCP interface: " +
                              std::string(std::strerror(errno)));
    return false;
  }

  connection_state_ = ConnectionState::CONNECTED;
  retry_backoff_ = middleware_timing::initial_tcp_retry_backoff;
  next_retry_time_ = std::chrono::steady_clock::now();
  slogger::success("TCP interface connected");
  return true;
}

bool TcpInterface::ensure_connected_or_retry_locked_() {
  if (connection_state_ == ConnectionState::CONNECTED && sock_fd_ >= 0) {
    return true;
  }

  auto now = std::chrono::steady_clock::now();
  if (now < next_retry_time_) {
    return false;
  }

  if (connect_socket_locked_()) {
    return true;
  }

  next_retry_time_ = now + retry_backoff_;
  auto next_backoff_ms =
      std::min<int64_t>(retry_backoff_.count() * 2,
                        middleware_timing::MAX_TCP_RETRY_BACKOFF.count());
  retry_backoff_ = std::chrono::milliseconds(next_backoff_ms);
  return false;
}

void TcpInterface::mark_disconnected_locked_(const std::string& reason) {
  bool was_connected = connection_state_ == ConnectionState::CONNECTED;
  connection_state_ = ConnectionState::DISCONNECTED_RETRYING;
  close_socket_locked_();
  if (was_connected) {
    slogger::warning(reason + ". Entering reconnect limbo.");
  } else {
    slogger::warning(reason);
  }
}

void TcpInterface::close_socket_locked_() {
  if (sock_fd_ >= 0) {
    close(sock_fd_);
    sock_fd_ = -1;
  }
}
