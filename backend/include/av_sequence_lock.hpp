#pragma once
#include <atomic>
#include <chrono>
#include <mutex>

#include "middleware_timing.hpp"
#include "warning_string.hpp"

// This file hosts locking mechanisms to orchestrate the packet sequence

class AvSequenceLock {
 public:
  AvSequenceLock(const WarningString);
  ~AvSequenceLock() = default;
  void lock();
  void unlock();
  bool is_locked();

 private:
  TimePoint getLastLockTime() const;
  bool unlock_if_timed_out_();
  std::mutex mtx_;
  const WarningString warningString;
  TimePoint last_lock_time_;
  // Time that you wait for a response from other device
  std::atomic<bool> is_locked_{false};
};
