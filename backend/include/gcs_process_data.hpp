#pragma once

/* Used to manage data that is generated on the GCS and is wanting to be sent
 * over radio
 */

#include <atomic>
#include <mutex>
#include <vector>
#include <zmq.hpp>

#include "av_sequence.hpp"
#include "middleware_timing.hpp"
#include "server_args.hpp"

// Singleton?
class PendantData {
 public:
  PendantData();
  std::vector<uint8_t> payload;

  // If you got no data, print timeout warning and update states
  void no_data();
  bool empty() { return payload.empty(); };

  // TODO Should be private at some point
  TimePoint last_receival_;
  TimePoint last_timeout_warning_time_;

 private:
  static inline const std::vector<uint8_t> FALLBACK_PAYLOAD_ = {0x02, 0x00,
                                                                0xFF, 0x00};
};

class WebsocketData {
 public:
  std::vector<uint8_t> payload;
  bool empty() { return payload.empty(); };
  void proccess_data_();  // should be private but cbf rn
  enum LastCommand {
    CAMERA_POWER_ON,
    CAMERA_POWER_OFF,
    CAMERA_MANUAL_CONTROL_ON,
    CAMERA_MANUAL_CONTROL_OFF,
    UNKNOWN,
  };
  LastCommand lastCommand = UNKNOWN;

 private:
  static constexpr uint8_t BYTES_PREFIX_POWER_ON_ = 123;
  static constexpr uint8_t BYTES_PREFIX_POWER_OFF_ = 100;
  static constexpr uint8_t BYTES_PREFIX_MANUAL_CONTROL_ON = 0xFF;
  static constexpr uint8_t BYTES_PREFIX_MANUAL_CONTROL_OFF = 0x00;
};

/// Thread-safe container for pendant and websocket data shared between
/// server_listen_loop (writer) and main loop (reader). Single mutex guards
/// all access; use the methods below instead of touching payload/lastCommand
/// directly.
class SharedGcsState {
 public:
  SharedGcsState() = default;

  // --- Writer (server_listen_loop) ---
  void set_pendant_received(std::vector<uint8_t> payload);
  void pendant_no_data();
  void set_websocket_received(std::vector<uint8_t> payload);

  // --- Reader (main loop) ---
  void get_snapshot(PendantData& pendant_out, WebsocketData& websocket_out);

 private:
  std::mutex mtx_;
  PendantData pendant_;
  WebsocketData websocket_;
};

// Just listen to requests from other processes
// Like the pendant and websocket
// Then update the data structs via SharedGcsState when they change
void server_listen_loop(zmq::context_t& all_context, const ParsedArgs args,
                        SharedGcsState& gcs_state,
                        std::atomic<bool>& server_running);

/// Copy ZMQ message bytes into a vector (for pendant or web control data).
std::vector<uint8_t> collect_pull_data(const zmq::message_t& last_pendant_msg);

/// Build GCS→AV command payload: packet ID, camera power bytes, broadcast flag.
std::vector<uint8_t> create_GCS_TO_AV_data(const bool BROADCAST,
                                           AvSequence& sequence);
