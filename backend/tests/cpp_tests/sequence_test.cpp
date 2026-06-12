#include <gtest/gtest.h>

#include <thread>

#include "av_sequence.hpp"

// AvSequence is designed as a process singleton (assert in ctor); only one
// AvSequence may exist. We use a single test that creates one and exercises
// AV-related behaviour only (GSE/mode/packet counts live in SharedGcsState).
// Diagram:
// https://github.com/RMIT-Hive-Rocketry/GCS/blob/main/notes/assets/sequence_diagram.png
TEST(SequenceTest, AvBehaviourOnly) {
  AvSequence seq;

  // Initial state
  EXPECT_EQ(seq.get_state(), AvSequence::LOOP_PRE_LAUNCH);
  EXPECT_FALSE(seq.start_sending_broadcast_flag());
  EXPECT_FALSE(seq.have_received_broadcast_flag());

  // State transitions
  seq.set_state(AvSequence::LOOP_IGNITION);
  EXPECT_EQ(seq.get_state(), AvSequence::LOOP_IGNITION);
  seq.set_state(AvSequence::LOOP_AV_DATA_TRANSMISSION_BURN);
  EXPECT_EQ(seq.get_state(), AvSequence::LOOP_AV_DATA_TRANSMISSION_BURN);
  seq.set_state(AvSequence::LOOP_PRE_LAUNCH);

  // AV await / received (when lock is locked we're waiting for AV response)
  EXPECT_FALSE(seq.waiting_for_av());  // initially unlocked, not waiting
  seq.start_await_av();
  EXPECT_TRUE(seq.waiting_for_av());  // locked = waiting for AV
  seq.received_av();
  EXPECT_FALSE(seq.waiting_for_av());  // unlocked again

  // sit_and_wait_for_av: need receiver thread to call received_av()
  seq.start_await_av();
  std::atomic<bool> done{false};
  std::thread receiver([&seq, &done]() {
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    seq.received_av();
    done = true;
  });
  seq.sit_and_wait_for_av();
  receiver.join();
  EXPECT_TRUE(done);
  EXPECT_FALSE(seq.waiting_for_av());  // unlocked after receive

  // Broadcast flags
  seq.set_start_sending_broadcast_flag(true);
  EXPECT_TRUE(seq.start_sending_broadcast_flag());
  seq.set_broadcast_flag_recieved(true);
  EXPECT_TRUE(seq.have_received_broadcast_flag());

  // Camera
  seq.set_camera_power(true);
  EXPECT_TRUE(seq.get_camera_power());
}
