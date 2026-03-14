#include "sequence.hpp"

#include <gtest/gtest.h>

#include <thread>

// Sequence is designed as a process singleton (assert in ctor); only one
// Sequence may exist. We use a single test that creates one and exercises all.
// Diagram:
// https://github.com/RMIT-Hive-Rocketry/GCS/blob/main/notes/assets/sequence_diagram.png
TEST(SequenceTest, AllBehaviour) {
  Sequence seq;

  // Initial state
  EXPECT_EQ(seq.get_state(), Sequence::LOOP_PRE_LAUNCH);
  EXPECT_FALSE(seq.gse_only_mode());
  EXPECT_FALSE(seq.manual_control_mode());
  EXPECT_EQ(seq.get_packet_count_av(), 0);
  EXPECT_EQ(seq.get_packet_count_gse(), 0);
  EXPECT_FALSE(seq.start_sending_broadcast_flag());
  EXPECT_FALSE(seq.have_received_broadcast_flag());

  // State transitions
  seq.set_state(Sequence::LOOP_IGNITION);
  EXPECT_EQ(seq.get_state(), Sequence::LOOP_IGNITION);
  seq.set_state(Sequence::LOOP_AV_DATA_TRANSMISSION_BURN);
  EXPECT_EQ(seq.get_state(), Sequence::LOOP_AV_DATA_TRANSMISSION_BURN);
  seq.set_state(Sequence::LOOP_PRE_LAUNCH);

  // GSE only mode
  // This is currently only set at initialisation time.
  // But I guess it can change during runtime for now?
  seq.set_gse_only_mode(true);
  EXPECT_TRUE(seq.gse_only_mode());
  seq.set_gse_only_mode(false);

  // GSE await / received (when lock is locked we're waiting for response)
  EXPECT_FALSE(seq.waiting_for_gse());  // initially unlocked, not waiting
  seq.start_await_gse();
  EXPECT_TRUE(seq.waiting_for_gse());  // locked = waiting for GSE
  seq.received_gse();
  EXPECT_FALSE(seq.waiting_for_gse());  // unlocked again

  // AV await / received
  EXPECT_FALSE(seq.waiting_for_av());
  seq.start_await_av();
  EXPECT_TRUE(seq.waiting_for_av());
  seq.received_av();
  EXPECT_FALSE(seq.waiting_for_av());

  // sit_and_wait_for_gse: need receiver thread to call received_gse()
  seq.start_await_gse();
  std::atomic<bool> done{false};
  std::thread receiver([&seq, &done]() {
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    seq.received_gse();
    done = true;
  });
  seq.sit_and_wait_for_gse();
  receiver.join();
  EXPECT_TRUE(done);
  EXPECT_FALSE(seq.waiting_for_gse());  // unlocked after receive

  // Packet counts
  seq.increment_packet_count_av();
  seq.increment_packet_count_av();
  seq.increment_packet_count_gse();
  EXPECT_EQ(seq.get_packet_count_av(), 2);
  EXPECT_EQ(seq.get_packet_count_gse(), 1);

  // Broadcast flags
  seq.set_start_sending_broadcast_flag(true);
  EXPECT_TRUE(seq.start_sending_broadcast_flag());
  seq.set_broadcast_flag_recieved(true);
  EXPECT_TRUE(seq.have_received_broadcast_flag());

  // Camera and manual control
  seq.set_camera_power(true);
  EXPECT_TRUE(seq.get_camera_power());
  seq.set_manual_control_mode(true);
  EXPECT_TRUE(seq.manual_control_mode());
}
