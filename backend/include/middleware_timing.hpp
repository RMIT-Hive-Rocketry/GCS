#pragma once

/// Include from main and any module that needs these values.

namespace middleware_timing {

// --- AvSequence lock (GSE/AV write wait timeout) ---
/// Time to wait for peer response before considering the lock timed out (ms).
constexpr int SEQUENCE_LOCK_TIMEOUT_MS = 1000;

// --- Command loop (pendant / web polling) ---
/// Poll timeout for ZMQ pendant and web control sockets (ms).
constexpr int COMMAND_LOOP_POLL_MS = 300;
/// After this many seconds without pendant data, use fallback and warn.
constexpr int PENDANT_FALLBACK_TIMEOUT_SECONDS = 5;
/// Minimum interval between repeated timeout warnings (seconds).
/// For terminal printing only. This does not effect functionality
constexpr int TIMEOUT_WARNING_INTERVAL_SECONDS = 3;

// --- Read loop (interface read thread) ---
/// Sleep when no data available to avoid busy-wait (ms).
constexpr int READ_LOOP_SLEEP_MS = 1;
/// After this many seconds with no data, log a "no data received" warning.
/// For terminal printing only. This does not effect functionality
constexpr int READ_LOOP_NO_DATA_WARNING_SECONDS = 3;

// --- GSE full-duplex rate limit (e.g. TCP; used when dual-interface is active)
// ---
/// Minimum interval between GSE sends when interface is full-duplex
/// (heartbeat). Send immediately if payload changed; otherwise throttle to this
/// interval (ms).
constexpr int GSE_FULL_DUPLEX_MIN_INTERVAL_MS = 500;

constexpr std::chrono::milliseconds initial_tcp_retry_backoff{250};
static constexpr int64_t MAX_TCP_RETRY_BACKOFF_MS = 2000;

}  // namespace middleware_timing
