#include "av_sequence.hpp"

#include <cassert>
#include <thread>

// AvSequence constructor.
// This object should be treated like a singleton,
// but passed by reference across threads instead of calling the constructor
// on each new instance
AvSequence::AvSequence() {
  assert(singleton_created_ == false);
  current_state = LOOP_PRE_LAUNCH;
  singleton_created_ = true;
  av_write_lock_.unlock();  // Constructor had set it unlocked anyway
}

// Are we waiting for a response from AV?
bool AvSequence::waiting_for_av() { return !av_write_lock_.is_locked(); }
bool AvSequence::sit_and_wait_for_av() {
  while (waiting_for_av()) {
    std::this_thread::sleep_for(middleware_timing::SEQUENCE_BUSY_WAIT);
  }
  return true;
}
void AvSequence::start_await_av() { av_write_lock_.lock(); }
void AvSequence::received_av() { av_write_lock_.unlock(); }
