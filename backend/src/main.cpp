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
#include "av_sequence.hpp"
#include "debug_functions.hpp"
#include "gcs_process_data.hpp"
#include "interface_factory.hpp"
#include "middleware_timing.hpp"
#include "packet_handling.hpp"
#include "server_args.hpp"
#include "subprocess_logging.hpp"
#include "tcp_interface.hpp"
#include "test_interface.hpp"
#include "test_uart_e5_interface.hpp"
#include "uart_e5_interface.hpp"

// This reads in all data and hosts the PUB/SUB IPC

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
                     zmq::socket_t& pub_socket, SharedGcsState& gcsState) {
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
            gcsState.increment_packet_count_av();
            std::unique_ptr<AV_TO_GCS_DATA_1> proto_msg =
                process_packet<AV_TO_GCS_DATA_1>(count, buffer, pub_socket,
                                                 READER_BOOT_TIME, gcsState);
            if (proto_msg == nullptr) {
              // Yeah we got it, so you can just continue talking to other
              // devices. But we assume it was garbage and the information in it
              // is fucked
              gcsState.av_sequence.received_av();
              break;
            }
            post_process_av(gcsState.av_sequence, proto_msg->flight_state());
            if (proto_msg->broadcast_flag()) {
              gcsState.av_sequence.set_broadcast_flag_recieved(true);
              gcsState.av_sequence.current_state =
                  AvSequence::LOOP_AV_DATA_TRANSMISSION_BURN;
            }
            break;
          }
          case AV_TO_GCS_DATA_2::ID: {  // 4
            gcsState.increment_packet_count_av();
            std::unique_ptr<AV_TO_GCS_DATA_2> proto_msg =
                process_packet<AV_TO_GCS_DATA_2>(count, buffer, pub_socket,
                                                 READER_BOOT_TIME, gcsState);
            if (proto_msg == nullptr) {
              gcsState.av_sequence.received_av();
              break;
            }
            post_process_av(gcsState.av_sequence, proto_msg->flight_state());
          } break;
          case AV_TO_GCS_DATA_3::ID: {  // 5
            gcsState.increment_packet_count_av();
            std::unique_ptr<AV_TO_GCS_DATA_3> proto_msg =
                process_packet<AV_TO_GCS_DATA_3>(count, buffer, pub_socket,
                                                 READER_BOOT_TIME, gcsState);
            if (proto_msg == nullptr) {
              gcsState.av_sequence.received_av();
              break;
            }
            post_process_av(gcsState.av_sequence, proto_msg->flight_state());
            break;
          }
          case GSE_TO_GCS_DATA_1::ID: {  // 6
            gcsState.increment_packet_count_gse();
            process_packet<GSE_TO_GCS_DATA_1>(count, buffer, pub_socket,
                                              READER_BOOT_TIME, gcsState);
            break;
          }
          case GSE_TO_GCS_DATA_2::ID: {  // 7
            gcsState.increment_packet_count_gse();
            process_packet<GSE_TO_GCS_DATA_2>(count, buffer, pub_socket,
                                              READER_BOOT_TIME, gcsState);
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
      std::this_thread::sleep_for(middleware_timing::READ_WRITE_LOOP_SLEEP);
      auto now = std::chrono::steady_clock::now();
      Seconds seconds_waited =
          std::chrono::duration_cast<Seconds>(now - last_read_time);
      Seconds seconds_waited_timeout =
          std::chrono::duration_cast<Seconds>(now - last_timeout_warning_time);
      if (seconds_waited >= middleware_timing::READ_LOOP_NO_DATA_WARNING &&
          seconds_waited_timeout >=
              middleware_timing::TIMEOUT_WARNING_INTERVAL) {
        slogger::warning("No data received for " +
                         std::to_string(seconds_waited.count()) + " seconds.");
        last_timeout_warning_time = now;
      }
    }
  }
}

void tcp_write(std::shared_ptr<RadioInterface> interface_gse,
               SharedGcsState& gcs_state) {
  std::vector<uint8_t> gse_payload;
  uint64_t observed_payload_version = 0;

  gcs_state.get_gse_payload_snapshot(gse_payload, observed_payload_version);
  if (!gse_payload.empty()) {
    interface_gse->write_data(gse_payload);
  }

  while (running) {
    gcs_state.wait_for_gse_payload_change(observed_payload_version,
                                          middleware_timing::TCP_HEARTBEAT);
    if (!running) {
      break;
    }

    gcs_state.get_gse_payload_snapshot(gse_payload, observed_payload_version);
    if (gse_payload.empty()) {
      continue;
    }

    // Wake reasons:
    // - payload version changed: send immediately for low-latency updates.
    // - timeout elapsed: resend latest payload as heartbeat.
    interface_gse->write_data(gse_payload);
  }
  slogger::debug("TCP write thread has closed");
}

int main(int argc, char* argv[]) {
  GOOGLE_PROTOBUF_VERIFY_VERSION;

  slogger::info("Starting middleware server");

  const ParsedArgs args = parse_args(argc, argv);

  signal(SIGINT, signal_handler);
  signal(SIGTERM, signal_handler);
  // Broken pipe: let TCP send() return EPIPE, don't kill process
  signal(SIGPIPE, SIG_IGN);

  // Data input reader from GCS processes (single mutex inside gcs_state)
  // Includes AV sequence data
  SharedGcsState gcs_state;
  gcs_state.set_gse_only_mode(args.gse_only_mode);

  std::shared_ptr<RadioInterface> interface_gse =
      create_interface(args.gse_type, args.gse_path);
  interface_gse->initialize();
  slogger::info("Interface [GSE] initialised with type: " + args.gse_type);

  std::optional<std::shared_ptr<RadioInterface>> interface_av;

  if (gcs_state.gse_only_mode()) {
    interface_av = std::nullopt;
  } else {
    std::shared_ptr<RadioInterface> interface_av_tmp;
    if (args.gse_type == args.av_type && args.gse_path == args.av_path) {
      interface_av_tmp = interface_gse;
      slogger::info("Interface  [AV] reusing GSE interface (same type/path)");
    } else {
      interface_av_tmp = create_interface(args.av_type, args.av_path, args.lora_cfg);
      interface_av_tmp->initialize();
      slogger::info("Interface  [AV] initialised with type: " + args.av_type);
    }
    interface_av = std::optional<std::shared_ptr<RadioInterface>>(interface_av_tmp);
  }

  zmq::context_t all_context(1);

  // PUB socket for broadcasting incoming data
  // why is this called pendant_socket_path? I think this is generic.
  // I will leave this to another commit to figure out
  zmq::socket_t pub_socket(all_context, ZMQ_PUB);
  pub_socket.bind("ipc:///tmp/" + args.pendant_socket_path + "_pub.sock");

  // Data input reader from AV or GSE (shared with GSE when same interface)
  std::optional<std::thread> av_reader;
  if (gcs_state.gse_only_mode()) {
    av_reader = std::nullopt;
  } else {
    av_reader = std::optional(std::thread(input_read_loop, interface_av.value(), std::ref(pub_socket), std::ref(gcs_state)));
  }

  std::thread gcs_reader(server_listen_loop, std::ref(all_context), args,
                         std::ref(gcs_state), std::ref(running));

  std::thread tcp_writer(tcp_write, std::ref(interface_gse),
                         std::ref(gcs_state));

  slogger::info("Middleware server started successfully");
  try {
    std::vector<uint8_t> main_gse_payload_probe;
    uint64_t main_observed_payload_version = 0;
    gcs_state.get_gse_payload_snapshot(main_gse_payload_probe,
                                       main_observed_payload_version);

    while (running) {
      PendantData pendant_data;
      WebsocketData websocket_data;
      gcs_state.get_snapshot(pendant_data, websocket_data);

      if (pendant_data.empty()) {
        // No data to send
        // This will only be empty while the pendant software boots
        // Fallback data should be present anyway?
        gcs_state.wait_for_gse_payload_change(
            main_observed_payload_version,
            middleware_timing::COMMAND_LOOP_POLL);
        gcs_state.get_gse_payload_snapshot(main_gse_payload_probe,
                                           main_observed_payload_version);
        continue;
      }

      if (!websocket_data.empty()) {
        switch (websocket_data.lastCommand) {
          case WebsocketData::CAMERA_POWER_ON:
            if (gcs_state.av_sequence.get_camera_power() != true) {
              slogger::warning("Camera power ON");
            }
            gcs_state.av_sequence.set_camera_power(true);
            break;
          case WebsocketData::CAMERA_POWER_OFF:
            if (gcs_state.av_sequence.get_camera_power() != false) {
              slogger::warning("Camera power OFF");
            }
            gcs_state.av_sequence.set_camera_power(false);
            break;
          case WebsocketData::CAMERA_MANUAL_CONTROL_ON:
            if (gcs_state.manual_control_mode() == false) {
              gcs_state.set_manual_control_mode(true);
              slogger::warning("Manual control ENABLED");
            }
            break;
          case WebsocketData::CAMERA_MANUAL_CONTROL_OFF:
            if (gcs_state.manual_control_mode() == true) {
              gcs_state.set_manual_control_mode(false);
              slogger::warning("Manual control DISABLED");
            }
            break;
          default:
            slogger::error("Unknown websocket command");
        }
      }

      if (gcs_state.gse_only_mode()) {
        gcs_state.wait_for_gse_payload_change(
            main_observed_payload_version,
            middleware_timing::COMMAND_LOOP_POLL);
        gcs_state.get_gse_payload_snapshot(main_gse_payload_probe,
                                           main_observed_payload_version);
        continue;  // Dont run the AV code below because it doesn't exist
      }

      bool av_broadcast =
          gcs_state.av_sequence.start_sending_broadcast_flag() &&
          !gcs_state.av_sequence.have_received_broadcast_flag();

      // After getting data, continue with main logic loop for avinoics.
      // GSE is on its own thread
      switch (gcs_state.av_sequence.get_state()) {
        case AvSequence::State::LOOP_PRE_LAUNCH:
          // Wait for data from GSE (blocking rest of this loop, or timeout)
          // Send data to AV
          interface_av.value()->write_data(
              create_GCS_TO_AV_data(av_broadcast, gcs_state.av_sequence));
          gcs_state.av_sequence.start_await_av();
          // Wait for data from AV (blocking rest of this loop, or timeout)
          gcs_state.av_sequence.sit_and_wait_for_av();
          break;
        case AvSequence::State::LOOP_IGNITION:
          // This stage is identical to pre-launch for GCS
          if (av_broadcast) {
            interface_av.value()->write_data(
                create_GCS_TO_AV_data(av_broadcast, gcs_state.av_sequence));
          }
          break;
        // It says once, but it's a conditional loop anyway.
        case AvSequence::State::ONCE_AV_DETERMINING_LAUNCH:
          interface_av.value()->write_data(
              create_GCS_TO_AV_data(av_broadcast, gcs_state.av_sequence));
          gcs_state.av_sequence.start_await_av();
          gcs_state.av_sequence.sit_and_wait_for_av();
          break;
        case AvSequence::State::LOOP_AV_DATA_TRANSMISSION_BURN:
          // Just listen. This thread can just close bassically
          if (av_broadcast) {
            interface_av.value()->write_data(
                create_GCS_TO_AV_data(av_broadcast, gcs_state.av_sequence));
          }
          break;
        case AvSequence::State::LOOP_AV_DATA_TRANSMISSION_APOGEE:
          // Just listen. This thread can just close bassically
          if (av_broadcast) {
            interface_av.value()->write_data(
                create_GCS_TO_AV_data(av_broadcast, gcs_state.av_sequence));
          }
          break;
        case AvSequence::State::LOOP_AV_DATA_TRANSMISSION_LANDED:
          // Just listen. This thread can just close bassically
          if (av_broadcast) {
            interface_av.value()->write_data(
                create_GCS_TO_AV_data(av_broadcast, gcs_state.av_sequence));
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
    gcs_reader.join();
    if (av_reader.has_value()) {
      av_reader.value().join();
    }
    tcp_writer.join();
    pub_socket.close();

    google::protobuf::ShutdownProtobufLibrary();
  } catch (const std::exception& e) {
    slogger::error("Error during cleanup");
    slogger::error(std::string(e.what()));
  }
  slogger::info("Middleware shutdown complete");
  return EXIT_SUCCESS;
}
