#include "gcs_commands.hpp"

#include "av_sequence.hpp"

std::vector<uint8_t> collect_pull_data(const zmq::message_t& last_pendant_msg) {
  return std::vector<uint8_t>(
      static_cast<const uint8_t*>(last_pendant_msg.data()),
      static_cast<const uint8_t*>(last_pendant_msg.data()) +
          last_pendant_msg.size());
}

std::vector<uint8_t> create_GCS_TO_AV_data(const bool BROADCAST,
                                           AvSequence& sequence) {
  std::vector<uint8_t> data;

  const bool camera_power = sequence.get_camera_power();

  data.push_back(0x01);  // Packet ID

  uint8_t byte1 = (0b101 << 5) | (camera_power << 4);
  data.push_back(byte1);

  uint8_t byte2 = (0b010 << 5) | ((!camera_power) << 4) | 0b1111;
  data.push_back(byte2);

  data.push_back(BROADCAST ? 0b10101010 : 0b00000000);

  return data;
}
