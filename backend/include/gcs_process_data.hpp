#pragma once

/* Used to manage data that is generated on the GCS and is wanting to be sent
 * over radio
 */

#include <atomic>
#include <condition_variable>
#include <cstdint>
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
/// server_listen_loop (gcs radio TX requests) and main loop (gcs radio RX).
/// Single mutex guards all access
/// Also contains the sequence data for Avionics E5 comms
class SharedGcsState {
 public:
  SharedGcsState() = default;

  // --- Writer (server_listen_loop) ---
  void set_pendant_received(std::vector<uint8_t> payload);
  void pendant_no_data();
  void set_websocket_received(std::vector<uint8_t> payload);

  // --- Reader (main loop) ---
  void get_snapshot(PendantData& pendant_out, WebsocketData& websocket_out);
  void set_gse_only_mode(bool mode) { gse_only_mode_ = mode; }
  bool gse_only_mode() const { return gse_only_mode_; }

  void set_manual_control_mode(bool mode);
  bool manual_control_mode() const;
  bool wait_for_gse_payload_change(uint64_t last_seen_version, Millis timeout);
  void get_gse_payload_snapshot(std::vector<uint8_t>& payload_out,
                                uint64_t& version_out) const;

  long get_packet_count_av() const { return packet_count_av_; }
  long get_packet_count_gse() const { return packet_count_gse_; }

  void increment_packet_count_av() { packet_count_av_++; }
  void increment_packet_count_gse() { packet_count_gse_++; }

  AvSequence av_sequence;

 private:
  std::vector<uint8_t> current_gse_payload_locked_() const;
  void notify_if_gse_payload_changed_locked_(
      const std::vector<uint8_t>& previous_payload);

  mutable std::mutex mtx_;
  std::condition_variable state_cv_;
  PendantData pendant_;
  WebsocketData websocket_;

  bool gse_only_mode_ = false;  // GSE only mode. This is an option from CLI
  bool manual_control_solenoids_ = false;  // Changes based on web data
  uint64_t gse_payload_version_ = 0;

  long packet_count_av_ = 0;
  long packet_count_gse_ = 0;
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
