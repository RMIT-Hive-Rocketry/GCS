#include "sequence.hpp"

#include <cassert>
#include <thread>

// AvSequence constrcutor.
// This object should be treated like a singleton,
// but passed by refference across threads instead of calling the constructor
// on each new instance
AvSequence::AvSequence() {
  assert(singleton_created_ == false);
  current_state = LOOP_PRE_LAUNCH;
  singleton_created_ = true;
  // First communication must be GCS -> GSE/AV. None talk without asking
  // This only applies pre launch confirmation
  gse_write_lock_.unlock();  // Constructor had set it unlocked anyway
  av_write_lock_.unlock();   // Constructor had set it unlocked anyway
}

// Are we waiting for a response from the GSE?
bool AvSequence::waiting_for_gse() { return !gse_write_lock_.is_locked(); }
// Wait until GSE responds while blocking the thread
bool AvSequence::sit_and_wait_for_gse() {
  while (waiting_for_gse()) {
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  return true;
}
void AvSequence::start_await_gse() { gse_write_lock_.lock(); }
void AvSequence::received_gse() { gse_write_lock_.unlock(); }

// Are we waiting for a response from AV?
bool AvSequence::waiting_for_av() { return !av_write_lock_.is_locked(); }
bool AvSequence::sit_and_wait_for_av() {
  while (waiting_for_av()) {
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  return true;
}
void AvSequence::start_await_av() { av_write_lock_.lock(); }
void AvSequence::received_av() { av_write_lock_.unlock(); }
