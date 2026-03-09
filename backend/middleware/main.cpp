#include <google/protobuf/stubs/common.h>
#include <signal.h>
#include <unistd.h>  // For debug sleep()

#include <atomic>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#include <zmq.hpp>

#include "AV_TO_GCS_DATA_1.hpp"
#include "AV_TO_GCS_DATA_1.pb.h"
#include "AV_TO_GCS_DATA_2.hpp"
#include "AV_TO_GCS_DATA_2.pb.h"
#include "AV_TO_GCS_DATA_3.hpp"
#include "AV_TO_GCS_DATA_3.pb.h"
#include "FlightState.pb.h"
#include "GSE_TO_GCS_DATA_1.hpp"
#include "GSE_TO_GCS_DATA_2.hpp"
#include "debug_functions.hpp"
#include "gcs_commands.hpp"
#include "interface_factory.hpp"
#include "middleware_timing.hpp"
#include "packet_handling.hpp"
#include "sequence.hpp"
#include "subprocess_logging.hpp"
#include "tcp_interface.hpp"
#include "test_interface.hpp"
#include "test_uart_e5_interface.hpp"
#include "uart_e5_interface.hpp"

// This file hosts the ZeroMQ IPC server stuff

std::atomic<bool> running{true};
volatile bool debugger_attached = false;

// Thread safe signal handler
void signal_handler(int) { running = false; }

inline void set_thread_name([[maybe_unused]] const char* name) {
#ifdef __APPLE__
  pthread_setname_np(name);
#endif
}

void input_read_loop(std::shared_ptr<RadioInterface> interface,
                     zmq::socket_t& pub_socket, Sequence& sequence) {
  set_thread_name("input_read_loop");
  std::vector<uint8_t> buffer(1024);
  auto READER_BOOT_TIME = std::chrono::steady_clock::now();
  auto last_read_time = READER_BOOT_TIME;
  auto last_timeout_warning_time = READER_BOOT_TIME;

  while (running) {
    ssize_t count = interface->read_data(buffer);
    if (count > 0) {
      last_read_time = std::chrono::steady_clock::now();
      // Check if we have enough bytes for the ID
      if (count >= 1) {
        int8_t packet_id = static_cast<int8_t>(buffer[0]);

        // Send packet ID to receiving ends so they know which proto file to use
        std::string packet_id_string(1, packet_id);
        zmq::message_t msg(packet_id_string.data(), sizeof(int8_t));
        pub_socket.send(msg, zmq::send_flags::none);

        // Note that some packet types are observed can be skipped if not meant
        // for GCS
        switch (packet_id) {
          case AV_TO_GCS_DATA_1::ID: {  // 3
            sequence.increment_packet_count_av();
            std::unique_ptr<AV_TO_GCS_DATA_1> proto_msg =
                process_packet<AV_TO_GCS_DATA_1>(count, buffer, pub_socket,
                                                 READER_BOOT_TIME, sequence);
            if (proto_msg == nullptr) {
              // Yeah we got it, so you can just continue talking to other
              // devices. But we assume it was garbage and the information in it
              // is fucked
              sequence.received_av();
              break;
            }
            post_process_av(sequence, proto_msg->flight_state());
            if (proto_msg->broadcast_flag()) {
              sequence.set_broadcast_flag_recieved(true);
              sequence.current_state = Sequence::LOOP_AV_DATA_TRANSMISSION_BURN;
            }
            break;
          }
          case AV_TO_GCS_DATA_2::ID: {  // 4
            sequence.increment_packet_count_av();
            std::unique_ptr<AV_TO_GCS_DATA_2> proto_msg =
                process_packet<AV_TO_GCS_DATA_2>(count, buffer, pub_socket,
                                                 READER_BOOT_TIME, sequence);
            if (proto_msg == nullptr) {
              sequence.received_av();
              break;
            }
            post_process_av(sequence, proto_msg->flight_state());
          } break;
          case AV_TO_GCS_DATA_3::ID: {  // 5
            sequence.increment_packet_count_av();
            std::unique_ptr<AV_TO_GCS_DATA_3> proto_msg =
                process_packet<AV_TO_GCS_DATA_3>(count, buffer, pub_socket,
                                                 READER_BOOT_TIME, sequence);
            if (proto_msg == nullptr) {
              sequence.received_av();
              break;
            }
            post_process_av(sequence, proto_msg->flight_state());
            break;
          }
          case GSE_TO_GCS_DATA_1::ID: {  // 6
            sequence.increment_packet_count_gse();
            process_packet<GSE_TO_GCS_DATA_1>(count, buffer, pub_socket,
                                              READER_BOOT_TIME, sequence);
            sequence.received_gse();
            break;
          }
          case GSE_TO_GCS_DATA_2::ID: {  // 7
            sequence.increment_packet_count_gse();
            process_packet<GSE_TO_GCS_DATA_2>(count, buffer, pub_socket,
                                              READER_BOOT_TIME, sequence);
            sequence.received_gse();
            break;
          }
          default: {
            std::string numeric_val =
                std::to_string(static_cast<int>(packet_id));
            slogger::error("Unknown packet ID: " + std::to_string(packet_id) +
                           " numeric: " + numeric_val);
            break;
          }
        }
      }
    } else {
      std::this_thread::sleep_for(
          std::chrono::milliseconds(middleware_timing::READ_LOOP_SLEEP_MS));
      auto now = std::chrono::steady_clock::now();
      int seconds_waited =
          std::chrono::duration_cast<std::chrono::seconds>(now - last_read_time)
              .count();
      int seconds_waited_timeout =
          std::chrono::duration_cast<std::chrono::seconds>(
              now - last_timeout_warning_time)
              .count();
      if (seconds_waited >=
              middleware_timing::READ_LOOP_NO_DATA_WARNING_SECONDS &&
          seconds_waited_timeout >=
              middleware_timing::TIMEOUT_WARNING_INTERVAL_SECONDS) {
        slogger::warning("No data received for " +
                         std::to_string(seconds_waited) + " seconds.");
        last_timeout_warning_time = now;
      }
    }
  }
}

int main(int argc, char* argv[]) {
  GOOGLE_PROTOBUF_VERIFY_VERSION;

  slogger::info("Starting middleware server");

  const std::string INTERFACE_NAME = std::string(argv[1]);
  const bool IS_UART = (INTERFACE_NAME == "UART");

  const int MIN_ARGS = IS_UART ? 14 : 5;  // 4 base + 9 lora + program name

  if (argc < MIN_ARGS) {
    slogger::error("Not enough arguments provided.");
    slogger::error(
        "Usage: ./file <interface type> <device path> <pendant socket path> "
        "<web control socket path> [optional mode]\n"
        "  UART also requires: <frequency> <spread_factor> <bandwidth> "
        "<tx_preamble> <rx_preamble> <power> <crc> <iq> <net>");
    throw std::runtime_error("Error: Not enough arguments provided");
    return EXIT_FAILURE;
  } else if (argc > MIN_ARGS + 1) {
    slogger::warning("Too many arguments provided: " + std::to_string(argc));
  }

  signal(SIGINT, signal_handler);
  signal(SIGTERM, signal_handler);

  const std::string DEVICE_PATH = std::string(argv[2]);
  const std::string PENDANT_SOCKET_PATH = std::string(argv[3]);
  const std::string WEB_CONTROL_SOCKET_PATH = std::string(argv[4]);

  LoraConfig lora_cfg;
  if (IS_UART) {
    lora_cfg = {
        .frequency = argv[5],
        .spread_factor = argv[6],
        .bandwidth = argv[7],
        .tx_preamble = argv[8],
        .rx_preamble = argv[9],
        .power = argv[10],
        .crc = argv[11],
        .iq = argv[12],
        .net = argv[13],
    };
  }

  std::shared_ptr<RadioInterface> interface =
      create_interface(INTERFACE_NAME, DEVICE_PATH, lora_cfg);

  interface->initialize();
  slogger::info("Interface initialised for type: " + std::string(argv[1]));

  // Create sequence handler singleton
  Sequence sequence;

  if (argc == 6) {
    std::string mode = std::string(argv[5]);
    sequence.set_gse_only_mode(mode == "--GSE_ONLY");
  }

  zmq::context_t context(1);

  // PUB socket for broadcasting incoming data
  zmq::socket_t pub_socket(context, ZMQ_PUB);
  pub_socket.bind("ipc:///tmp/" + PENDANT_SOCKET_PATH + "_pub.sock");

  // Only keep this many messages in buffer.
  constexpr int PULL_SOCKET_HWM = 1;

  // PULL socket for fowarding commands to LoRa
  zmq::socket_t pendant_pull_socket(context, ZMQ_PULL);
  pendant_pull_socket.set(zmq::sockopt::rcvhwm, PULL_SOCKET_HWM);
  pendant_pull_socket.set(zmq::sockopt::conflate, 1);
  pendant_pull_socket.bind("ipc:///tmp/" + PENDANT_SOCKET_PATH +
                           "_pendant_pull.sock");

  zmq::socket_t web_control_pull_socket(context, ZMQ_PULL);
  web_control_pull_socket.set(zmq::sockopt::rcvhwm, PULL_SOCKET_HWM);
  // Only keep last message
  web_control_pull_socket.set(zmq::sockopt::conflate, 1);
  web_control_pull_socket.bind("ipc://" + WEB_CONTROL_SOCKET_PATH);

  // Start interface reading thread
  std::thread reader(input_read_loop, interface, std::ref(pub_socket),
                     std::ref(sequence));

  // http://api.zeromq.org/3-0:zmq-poll
  // Can add multiple push pull sockets here. Useful for when front end is
  // integrated
  std::vector<zmq::pollitem_t> items = {
      {static_cast<void*>(pendant_pull_socket), 0, ZMQ_POLLIN, 0},
      {static_cast<void*>(web_control_pull_socket), 0, ZMQ_POLLIN, 0}};
  std::vector<uint8_t> pendant_data;
  std::vector<uint8_t> web_control_data;

  const std::vector<uint8_t> FALLBACK_PENDANT_DATA = {0x02, 0x00, 0xFF, 0x00};
  auto last_pendant_receival = std::chrono::steady_clock::now();
  auto last_timeout_warning_time = std::chrono::steady_clock::now();
  // TODO I think this is redundant now?
  const bool SUPPRESS_PENDANT_WARNING = std::getenv("CONFIG_PATH") == nullptr;
  // Main command loop
  slogger::info("Middleware server started successfully");
  try {
    while (running) {
      zmq::poll(items, std::chrono::milliseconds(
                           middleware_timing::COMMAND_LOOP_POLL_MS));

      int pendant_socket_more_intbool =
          1;  // http://api.zeromq.org/2-2:zmq-getsockopt
      // items[0].revents represents items[0] which is the pendant data
      if (items[0].revents & ZMQ_POLLIN) {
        do {  // Data to be dequeued
          last_pendant_receival = std::chrono::steady_clock::now();
          zmq::message_t pendant_msg;
          zmq::recv_result_t pendant_result =
              pendant_pull_socket.recv(pendant_msg, zmq::recv_flags::none);
          if (pendant_result) {
            pendant_data = collect_pull_data(pendant_msg);
            pendant_socket_more_intbool =
                pendant_pull_socket.get(zmq::sockopt::rcvmore);
          }
        } while (pendant_socket_more_intbool);
      } else {
        auto now = std::chrono::steady_clock::now();
        int seconds_waited = std::chrono::duration_cast<std::chrono::seconds>(
                                 now - last_pendant_receival)
                                 .count();
        int seconds_waited_timeout =
            std::chrono::duration_cast<std::chrono::seconds>(
                now - last_timeout_warning_time)
                .count();
        if (seconds_waited >=
                middleware_timing::PENDANT_FALLBACK_TIMEOUT_SECONDS &&
            seconds_waited_timeout >=
                middleware_timing::TIMEOUT_WARNING_INTERVAL_SECONDS) {
          if (!SUPPRESS_PENDANT_WARNING) {
            slogger::warning(
                "Failed to get any new pendant data from pendant service "
                "for " +
                std::to_string(seconds_waited) + " seconds");
          }
          pendant_data = FALLBACK_PENDANT_DATA;
          last_timeout_warning_time = now;
        }
      }

      if (pendant_data.empty()) {
        // No data to send, continue and try polling again
        // This will only be empty while the pendant software boots
        // Fallback data should be present anyway
        continue;
      }

      // http://api.zeromq.org/2-2:zmq-getsockopt
      int web_control_socket_more_intbool = 1;
      if (items[1].revents & ZMQ_POLLIN) {
        do {  // Data to be dequeued
          zmq::message_t web_control_msg;
          zmq::recv_result_t web_control_result = web_control_pull_socket.recv(
              web_control_msg, zmq::recv_flags::none);
          if (web_control_result) {
            web_control_data = collect_pull_data(web_control_msg);
            web_control_socket_more_intbool =
                web_control_pull_socket.get(zmq::sockopt::rcvmore);
          }
        } while (web_control_socket_more_intbool);
        // Get rid of this shit when you refactor all IPC comms
        if (!web_control_data.empty()) {
          slogger::debug("server got values from web control: " +
                         debug::vectorToHexString(web_control_data,
                                                  web_control_data.size()));
          uint8_t packet_byte_prefix = web_control_data.front();
          web_control_data.erase(
              web_control_data.begin());  // remove that first byte
          // fucking stupid check because grpc didn't get done in time
          // fuck
          if (packet_byte_prefix == 123) {
            // Yeah you're trying to activate power
            if (sequence.get_camera_power() != true) {
              slogger::warning("Camera power ON");
            }
            sequence.set_camera_power(true);
          } else if (packet_byte_prefix == 100) {
            if (sequence.get_camera_power() != false) {
              slogger::warning("Camera power OFF");
            }
            sequence.set_camera_power(false);
          } else {
            bool manual_control = packet_byte_prefix == 0xFF;
            if (manual_control != sequence.manual_control_mode()) {
              // manual control state value has changed
              if (manual_control) {
                slogger::warning("Manual control ENABLED");
              } else {
                slogger::warning("Manual control DISABLED");
              }
            }
            sequence.set_manual_control_mode(manual_control);
          }
        }
      }

      // Are we sending manual packets or pendant controlled packets?
      // You have to pick something to continue the networking sequence and not
      // timeout the GSE
      std::vector<uint8_t> gse_data;
      if (sequence.manual_control_mode()) {
        gse_data = web_control_data;  // Last updated value
      } else {
        gse_data = pendant_data;
      }

      if (sequence.gse_only_mode()) {
        interface->write_data(gse_data);
        sequence.start_await_gse();
        sequence.sit_and_wait_for_gse();
        continue;
      }

      bool broadcast = sequence.start_sending_broadcast_flag() &&
                       !sequence.have_received_broadcast_flag();

      // After getting data, continue with main logic loop
      switch (sequence.get_state()) {
        case Sequence::State::LOOP_PRE_LAUNCH:
          // Send data to GSE
          interface->write_data(gse_data);
          sequence.start_await_gse();
          // Wait for data from GSE (blocking rest of this loop, or timeout)
          sequence.sit_and_wait_for_gse();  // Let read thread unlock this
          // Send data to AV
          interface->write_data(create_GCS_TO_AV_data(broadcast, sequence));
          sequence.start_await_av();
          // Wait for data from AV (blocking rest of this loop, or timeout)
          sequence.sit_and_wait_for_av();
          break;
        case Sequence::State::LOOP_IGNITION:
          // This stage is identical to pre-launch for GCS
          if (broadcast) {
            interface->write_data(create_GCS_TO_AV_data(broadcast, sequence));
          }
          break;
        // It says once, but it's a conditional loop anyway.
        case Sequence::State::ONCE_AV_DETERMINING_LAUNCH:
          interface->write_data(gse_data);
          sequence.start_await_gse();
          sequence.sit_and_wait_for_gse();
          interface->write_data(create_GCS_TO_AV_data(broadcast, sequence));
          sequence.start_await_av();
          sequence.sit_and_wait_for_av();
          break;
        case Sequence::State::LOOP_AV_DATA_TRANSMISSION_BURN:
          // Just listen. This thread can just close bassically
          if (broadcast) {
            interface->write_data(create_GCS_TO_AV_data(broadcast, sequence));
          }
          break;
        case Sequence::State::LOOP_AV_DATA_TRANSMISSION_APOGEE:
          // Just listen. This thread can just close bassically
          if (broadcast) {
            interface->write_data(create_GCS_TO_AV_data(broadcast, sequence));
          }
          break;
        case Sequence::State::LOOP_AV_DATA_TRANSMISSION_LANDED:
          // Just listen. This thread can just close bassically
          if (broadcast) {
            interface->write_data(create_GCS_TO_AV_data(broadcast, sequence));
          }
          break;
      }
    }
    slogger::info("Middleware shutdown starting");
  } catch (const zmq::error_t& e) {
    // EINTR (signal interrupt) is expected on shutdown
    if (e.num() != EINTR) {
      slogger::error("ZeroMQ.1 error (" + std::to_string(e.num()) +
                     "): " + std::string(e.what()));
      throw;
    }
  } catch (const std::runtime_error& e) {
    slogger::error("Runtime error: " + std::string(e.what()));
    throw;
  } catch (const std::exception& e) {
    slogger::error("Generic error on main: " + std::string(e.what()));
    throw;
  }
  try {
    // Cleanup
    reader.join();
    pub_socket.close();
    pendant_pull_socket.close();
    web_control_pull_socket.close();
    context.close();
    google::protobuf::ShutdownProtobufLibrary();
  } catch (const std::exception& e) {
    slogger::error("Error during cleanup");
    slogger::error(std::string(e.what()));
  }
  slogger::info("Middleware shutdown complete");
  return EXIT_SUCCESS;
}
