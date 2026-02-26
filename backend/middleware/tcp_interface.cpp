// tcp_interface.cpp
#include "tcp_interface.hpp"

#include <arpa/inet.h>
#include <fcntl.h>
#include <netinet/tcp.h>
#include <sys/socket.h>
#include <unistd.h>

#include <chrono>
#include <cstring>
#include <stdexcept>
#include <system_error>
#include <thread>

#include "subprocess_logging.hpp"

namespace {
constexpr const char* kDefaultIp = "127.0.0.1";  // Static IP
constexpr uint16_t kDefaultPort = 5000;          // Static port
}  // namespace

TcpInterface::TcpInterface(const std::string& endpoint)
    : ip_(kDefaultIp), port_(kDefaultPort) {
  parse_endpoint(endpoint);
}

TcpInterface::~TcpInterface() {
  std::lock_guard<std::recursive_mutex> lock(io_mutex_);
  if (sock_fd_ >= 0) {
    close(sock_fd_);
    sock_fd_ = -1;
  }
}

void TcpInterface::parse_endpoint(const std::string& endpoint) {
  if (endpoint.empty()) return;

  auto pos = endpoint.find(':');
  if (pos == std::string::npos) {
    ip_ = endpoint;
    return;
  }

  ip_ = endpoint.substr(0, pos);
  try {
    int p = std::stoi(endpoint.substr(pos + 1));
    if (p > 0 && p <= 65535) {
      port_ = static_cast<uint16_t>(p);
    }
  } catch (...) {
    // Fall back to default port on parse errors.
  }
}

bool TcpInterface::initialize() {
  std::lock_guard<std::recursive_mutex> lock(io_mutex_);

  sock_fd_ = ::socket(AF_INET, SOCK_STREAM, 0);
  if (sock_fd_ < 0) {
    throw std::system_error(errno, std::system_category(),
                            "Failed to create TCP socket");
  }

  // Disable Nagle's algorithm for low-latency sends.
  int flag = 1;
  if (setsockopt(sock_fd_, IPPROTO_TCP, TCP_NODELAY, &flag, sizeof(flag)) < 0) {
    slogger::warning("Failed to set TCP_NODELAY on socket");
  }

  std::memset(&remote_addr_, 0, sizeof(remote_addr_));
  remote_addr_.sin_family = AF_INET;
  remote_addr_.sin_port = htons(port_);
  if (inet_pton(AF_INET, ip_.c_str(), &remote_addr_.sin_addr) <= 0) {
    throw std::runtime_error("Invalid TCP interface IP address: " + ip_);
  }

  slogger::info("Connecting TCP interface to " + ip_ + ":" +
                std::to_string(port_));

  if (::connect(sock_fd_, reinterpret_cast<sockaddr*>(&remote_addr_),
                sizeof(remote_addr_)) < 0) {
    int err = errno;
    throw std::system_error(err, std::system_category(),
                            "Failed to connect TCP interface");
  }

  return true;
}

ssize_t TcpInterface::write_data(const std::vector<uint8_t>& data) {
  std::lock_guard<std::recursive_mutex> lock(io_mutex_);
  if (sock_fd_ < 0) {
    slogger::error("TCP socket not connected for write");
    return -1;
  }

  const uint8_t* buf = data.data();
  size_t total = 0;
  while (total < data.size()) {
    ssize_t n = ::send(sock_fd_, buf + total, data.size() - total, 0);
    if (n < 0) {
      if (errno == EINTR) continue;
      slogger::error("TCP send failed");
      throw std::system_error(errno, std::system_category(), "TCP send failed");
    }
    if (n == 0) break;
    total += static_cast<size_t>(n);
  }

  return static_cast<ssize_t>(total);
}

ssize_t TcpInterface::read_data(std::vector<uint8_t>& buffer) {
  std::lock_guard<std::recursive_mutex> lock(io_mutex_);
  if (sock_fd_ < 0) {
    slogger::error("TCP socket not connected for read");
    return -1;
  }

  if (buffer.empty()) {
    return 0;
  }

  // Basic blocking read with a small timeout using select.
  fd_set read_fds;
  FD_ZERO(&read_fds);
  FD_SET(sock_fd_, &read_fds);

  timeval timeout{};
  timeout.tv_sec = 0;
  timeout.tv_usec = 100000;  // 100ms

  int ready = ::select(sock_fd_ + 1, &read_fds, nullptr, nullptr, &timeout);
  if (ready < 0) {
    if (errno == EINTR) return 0;
    throw std::system_error(errno, std::system_category(), "TCP select failed");
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
    throw std::system_error(errno, std::system_category(), "TCP recv failed");
  }

  return n;
}
