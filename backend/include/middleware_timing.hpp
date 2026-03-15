#pragma once

/// Include from main and any module that needs these values.

// Holy fuck these types are long
using TimePoint = std::chrono::time_point<std::chrono::steady_clock>;
using Seconds = std::chrono::seconds;
using Millis = std::chrono::milliseconds;

namespace middleware_timing {

// --- AvSequence and lock (GSE/AV write wait timeout) ---
/// Time to wait for peer response before considering the lock timed out and
/// device unresponsive
constexpr Millis SEQUENCE_LOCK_TIMEOUT{1000};
/// Buffer time while busy waiting on thread
constexpr Millis SEQUENCE_BUSY_WAIT{10};

// --- Command loop (pendant / web polling) ---
/// Poll timeout for ZMQ pendant and web control sockets (ms).
constexpr Millis COMMAND_LOOP_POLL{300};
/// After this many seconds without pendant data, use fallback and warn.
constexpr Seconds PENDANT_FALLBACK_TIMEOUT{5};
/// Minimum interval between repeated timeout warnings (seconds).
/// For terminal printing only. This does not effect functionality
constexpr Seconds TIMEOUT_WARNING_INTERVAL{10};

// --- Read loop (interface read thread) ---
/// Sleep when no data available to avoid busy-wait (ms).
constexpr Millis READ_LOOP_SLEEP{1};
/// After this many seconds with no data, log a "no data received" warning.
/// For terminal printing only. This does not effect functionality
constexpr Seconds READ_LOOP_NO_DATA_WARNING{3};

// --- TCP write heartbeat ---
/// Minimum interval between sending the same TCP payload.
/// If a payload is unchanged and was sent within this interval, skip it.
/// If payload changes, send immediately.
constexpr Millis TCP_HEARTBEAT{500};

/// Include desc
constexpr Millis initial_tcp_retry_backoff{250};
/// Include desc
static constexpr Millis MAX_TCP_RETRY_BACKOFF{2000};

}  // namespace middleware_timing
