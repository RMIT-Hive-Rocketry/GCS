// test_uart_e5_interface.hpp
#pragma once

#include <termios.h>

#include <chrono>
#include <mutex>
#include <string>
#include <vector>

#include "radio_interface.hpp"

class TestUartE5Interface : public RadioInterface {
 public:
  TestUartE5Interface(const std::string& device_path, int baud_rate = B115200);
  virtual ~TestUartE5Interface();

  bool initialize() override;
  ssize_t read_data(std::vector<uint8_t>& buffer) override;
  ssize_t write_data(const std::vector<uint8_t>& data) override;

 private:
  std::recursive_mutex io_mutex_;
  int baud_rate_;
  int uart_fd_ = -1;
  std::string device_path_;

  void configure_test_uart();
};
