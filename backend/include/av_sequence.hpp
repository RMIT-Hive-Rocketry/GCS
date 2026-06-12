#pragma once
#include "av_sequence_lock.hpp"

// Used for handling position in the sequence diagram.
// This should be treated as a singleton, passed by `std::ref` through threads
class AvSequence {
 public:
  AvSequence();
  ~AvSequence() = default;

  // Current state in the sequence diagram
  enum State {
    LOOP_PRE_LAUNCH,
    LOOP_IGNITION,
    ONCE_AV_DETERMINING_LAUNCH,
    LOOP_AV_DATA_TRANSMISSION_BURN,    // For motor burn and coasting
    LOOP_AV_DATA_TRANSMISSION_APOGEE,  // During and post apogee
    LOOP_AV_DATA_TRANSMISSION_LANDED   // Landed / recovery
  };

  void set_state(State state) { current_state = state; }
  State get_state() const { return current_state; }

  bool waiting_for_av();
  bool sit_and_wait_for_av();
  void start_await_av();
  void received_av();

  State current_state;

  bool start_sending_broadcast_flag() const {
    return start_sending_broadcast_flag_;
  }
  void set_start_sending_broadcast_flag(bool flag) {
    start_sending_broadcast_flag_ = flag;
  }

  bool have_received_broadcast_flag() const { return broadcast_flag_recieved_; }
  void set_broadcast_flag_recieved(bool flag) {
    broadcast_flag_recieved_ = flag;
  }

  bool get_camera_power() const { return camera_power_; }
  void set_camera_power(bool flag) { camera_power_ = flag; }

 private:
  AvSequenceLock av_write_lock_{AV};

  bool start_sending_broadcast_flag_ = false;
  bool broadcast_flag_recieved_ = false;
  bool camera_power_ = false;
  bool singleton_created_ = false;
};
