#include "interface_factory.hpp"

#include <gtest/gtest.h>

#include <memory>

#include "tcp_interface.hpp"
#include "test_interface.hpp"
#include "test_uart_e5_interface.hpp"
#include "uart_e5_interface.hpp"

using namespace std;

TEST(InterfaceFactoryTest, CreateUartE5) {
  LoraConfig lora_cfg{};
  shared_ptr<RadioInterface> interface =
      create_interface("UART_E5", "/dev/null", lora_cfg);
  ASSERT_NE(interface, nullptr);
  EXPECT_NE(dynamic_pointer_cast<UartE5Interface>(interface), nullptr);
}

TEST(InterfaceFactoryTest, CreateTest) {
  shared_ptr<RadioInterface> interface = create_interface("TEST", "/dev/null");
  ASSERT_NE(interface, nullptr);
  EXPECT_NE(dynamic_pointer_cast<TestInterface>(interface), nullptr);
}

TEST(InterfaceFactoryTest, CreateTestUartE5) {
  shared_ptr<RadioInterface> interface =
      create_interface("TEST_UART_E5", "/dev/null");
  ASSERT_NE(interface, nullptr);
  EXPECT_NE(dynamic_pointer_cast<TestUartE5Interface>(interface), nullptr);
}

TEST(InterfaceFactoryTest, CreateTcp) {
  shared_ptr<RadioInterface> interface =
      create_interface("TCP", "127.0.0.1:9999");
  ASSERT_NE(interface, nullptr);
  EXPECT_NE(dynamic_pointer_cast<TcpInterface>(interface), nullptr);
}

TEST(InterfaceFactoryTest, InvalidTypeThrows) {
  EXPECT_THROW(create_interface("INVALID", "/dev/null"), std::runtime_error);
}

TEST(InterfaceFactoryTest, InvalidTcpEndpointThrows) {
  EXPECT_THROW(create_interface("TCP", "no-colon"), std::runtime_error);
  EXPECT_THROW(create_interface("TCP", ":5000"), std::runtime_error);
  EXPECT_THROW(create_interface("TCP", "127.0.0.1:"), std::runtime_error);
  EXPECT_THROW(create_interface("TCP", "127.0.0.1:99999"), std::runtime_error);
  EXPECT_THROW(create_interface("TCP", "127.0.0.1:a5000"), std::runtime_error);
  EXPECT_THROW(create_interface("TCP", "127.0.0.1.0:5000"), std::runtime_error);
  EXPECT_THROW(create_interface("TCP", "300.0.0.1.0:5000"), std::runtime_error);
  EXPECT_THROW(create_interface("TCP", "127.0..1.0:5000"), std::runtime_error);
  EXPECT_THROW(create_interface("TCP", "127.01.0:5000"), std::runtime_error);
  EXPECT_THROW(create_interface("TCP", ""), std::runtime_error);
}
