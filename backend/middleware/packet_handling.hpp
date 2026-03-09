#pragma once

#include <chrono>
#include <memory>
#include <string>
#include <vector>

#include "FlightState.pb.h"
#include "debug_functions.hpp"
#include "sequence.hpp"
#include "subprocess_logging.hpp"
#include <zmq.hpp>

/// Process a single packet: parse from buffer, convert to protobuf, send on
/// pub_socket, run sequence updates. SIZE does not include the ID byte.
/// Returns the parsed payload or nullptr on error.
template <typename PacketType>
std::unique_ptr<PacketType> process_packet(
    const ssize_t BUFFER_BYTE_COUNT,
    std::vector<uint8_t>& buffer,
    zmq::socket_t& pub_socket,
    const std::chrono::steady_clock::time_point& READER_BOOT_TIME,
    Sequence& sequence) {
  if (BUFFER_BYTE_COUNT >= PacketType::SIZE + 1) {
    try {
      std::unique_ptr<PacketType> payload =
          std::make_unique<PacketType>(&buffer[1]);

      float TIMESTAMP = std::chrono::duration<float>(
                            std::chrono::steady_clock::now() - READER_BOOT_TIME)
                            .count();
      auto proto_msg =
          payload->toProtobuf(TIMESTAMP, sequence.get_packet_count_av(),
                              sequence.get_packet_count_gse());
      if (!proto_msg.IsInitialized()) {
        std::string missing_info = proto_msg.InitializationErrorString();
        slogger::warning(std::string(PacketType::PACKET_NAME) +
                         ": Not all fields are initialized in the protobuf "
                         "message. Missing: " +
                         missing_info);
      }
      std::string serialized;
      if (proto_msg.SerializeToString(&serialized)) {
        zmq::message_t msg(serialized.data(), serialized.size());
        pub_socket.send(msg, zmq::send_flags::none);
      } else {
        slogger::error(
            std::string(PacketType::PACKET_NAME) +
            ": Failed to serialize and send to string with protobuf");
        return nullptr;
      }
      return payload;
    } catch (const std::exception& e) {
      slogger::error(std::string(PacketType::PACKET_NAME) +
                     ": Error processing payload: " + e.what());
    } catch (...) {
      slogger::error("Caught unknown exception while processing payload");
    }
  } else {
    slogger::error(std::string(PacketType::PACKET_NAME) +
                   ": Incorrect packet size. Expected: " +
                   std::to_string(PacketType::SIZE + 1) + " bytes, got: " +
                   std::to_string(BUFFER_BYTE_COUNT) + " bytes");
    slogger::debug("Buffer contents: " +
                   debug::vectorToHexString(buffer, BUFFER_BYTE_COUNT));
  }
  return nullptr;
}

/// Post-process after receiving an AV packet: update sequence (received_av,
/// state, broadcast flags) based on flight state.
void post_process_av(Sequence& sequence,
                     const common::FlightState FLIGHT_STATE);
