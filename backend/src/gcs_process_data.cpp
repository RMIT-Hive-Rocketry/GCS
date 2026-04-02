#include "gcs_process_data.hpp"

#include "debug_functions.hpp"
#include "middleware_timing.hpp"
#include "server_args.hpp"
#include "subprocess_logging.hpp"

void PendantData::no_data() {
  auto now = std::chrono::steady_clock::now();

  if ((now - last_receival_) >= (middleware_timing::PENDANT_FALLBACK_TIMEOUT)) {
    payload = FALLBACK_PAYLOAD_;
  }

  if ((now - last_timeout_warning_time_) >=
      (middleware_timing::TIMEOUT_WARNING_INTERVAL)) {
    auto waited = now - last_receival_;
    auto sec_waited = (std::chrono::duration_cast<Seconds>(waited).count());
    slogger::warning(
        "Failed to get any new pendant data from pendant service "
        "for " +
        std::to_string(sec_waited) + " seconds" +
        ". This is OK if controller = emulated_device");
    last_timeout_warning_time_ = now;
  }
}

PendantData::PendantData() {
  auto t = std::chrono::steady_clock::now();
  last_receival_ = t;
  last_timeout_warning_time_ = t;
}

void SharedGcsState::set_pendant_received(std::vector<uint8_t> payload) {
  std::lock_guard<std::mutex> lock(mtx_);
  const std::vector<uint8_t> previous_payload = current_gse_payload_locked_();
  pendant_.last_receival_ = std::chrono::steady_clock::now();
  pendant_.payload = std::move(payload);
  notify_if_gse_payload_changed_locked_(previous_payload);
}

void SharedGcsState::pendant_no_data() {
  std::lock_guard<std::mutex> lock(mtx_);
  const std::vector<uint8_t> previous_payload = current_gse_payload_locked_();
  pendant_.no_data();
  notify_if_gse_payload_changed_locked_(previous_payload);
}

void SharedGcsState::set_websocket_received(std::vector<uint8_t> payload) {
  std::lock_guard<std::mutex> lock(mtx_);
  const std::vector<uint8_t> previous_payload = current_gse_payload_locked_();
  websocket_.payload = std::move(payload);
  websocket_.proccess_data_();
  notify_if_gse_payload_changed_locked_(previous_payload);
}

void SharedGcsState::get_snapshot(PendantData& pendant_out,
                                  WebsocketData& websocket_out) {
  std::lock_guard<std::mutex> lock(mtx_);
  pendant_out = pendant_;
  websocket_out = websocket_;
}

void SharedGcsState::set_manual_control_mode(bool mode) {
  std::lock_guard<std::mutex> lock(mtx_);
  if (manual_control_solenoids_ == mode) {
    return;
  }
  const std::vector<uint8_t> previous_payload = current_gse_payload_locked_();
  manual_control_solenoids_ = mode;
  notify_if_gse_payload_changed_locked_(previous_payload);
}

bool SharedGcsState::manual_control_mode() const {
  std::lock_guard<std::mutex> lock(mtx_);
  return manual_control_solenoids_;
}

bool SharedGcsState::wait_for_gse_payload_change(uint64_t last_seen_version,
                                                 Millis timeout) {
  std::unique_lock<std::mutex> lock(mtx_);
  return state_cv_.wait_for(lock, timeout, [this, last_seen_version] {
    return gse_payload_version_ != last_seen_version;
  });
}

void SharedGcsState::get_gse_payload_snapshot(std::vector<uint8_t>& payload_out,
                                              uint64_t& version_out) const {
  std::lock_guard<std::mutex> lock(mtx_);
  payload_out = current_gse_payload_locked_();
  version_out = gse_payload_version_;
}

std::vector<uint8_t> SharedGcsState::current_gse_payload_locked_() const {
  return manual_control_solenoids_ ? websocket_.payload : pendant_.payload;
}

// Tell everyone listening into events if the payload has changed
void SharedGcsState::notify_if_gse_payload_changed_locked_(
    const std::vector<uint8_t>& previous_payload) {
  const std::vector<uint8_t> current_payload = current_gse_payload_locked_();
  if (current_payload == previous_payload) {
    return;
  }

  ++gse_payload_version_;
  state_cv_.notify_all();
}

// Other pendant IPC comms have no header information.
// The data from the websocket has some header information.
// This method will strip it and process it accordingly
void WebsocketData::proccess_data_() {
  // Get rid of this shit when you refactor all IPC comms
  // GRPC would be nicer than random bytes sent over IPC
  if (empty()) {
    return;
  }

  slogger::debug("server got values from web control: " +
                 debug::vectorToHexString(payload, payload.size()));
  uint8_t payload_prefix = payload.front();
  payload.erase(payload.begin());  // remove first byte

  // fucking stupid check because grpc didn't get done in time
  // fuck
  // look at this magic bs
  switch (payload_prefix) {
    case BYTES_PREFIX_POWER_ON_:
      lastCommand = CAMERA_POWER_ON;
      break;
    case BYTES_PREFIX_POWER_OFF_:
      lastCommand = CAMERA_POWER_OFF;
      break;
    case BYTES_PREFIX_MANUAL_CONTROL_ON:
      lastCommand = CAMERA_MANUAL_CONTROL_ON;
      break;
    case BYTES_PREFIX_MANUAL_CONTROL_OFF:
      lastCommand = CAMERA_MANUAL_CONTROL_OFF;
      break;
    default:
      lastCommand = UNKNOWN;
  }
}

void server_listen_loop(zmq::context_t& all_context, const ParsedArgs args,
                        SharedGcsState& gcs_state,
                        std::atomic<bool>& server_running) {
  // Only keep this many messages in buffer.
  constexpr int PULL_SOCKET_HWM = 1;

  // PULL socket for fowarding commands to LoRa
  zmq::socket_t pendant_pull_socket(all_context, ZMQ_PULL);
  pendant_pull_socket.set(zmq::sockopt::rcvhwm, PULL_SOCKET_HWM);
  pendant_pull_socket.set(zmq::sockopt::conflate, 1);
  pendant_pull_socket.bind("ipc:///tmp/" + args.pendant_socket_path +
                           "_pendant_pull.sock");

  zmq::socket_t web_control_pull_socket(all_context, ZMQ_PULL);
  web_control_pull_socket.set(zmq::sockopt::rcvhwm, PULL_SOCKET_HWM);
  // Only keep last message
  web_control_pull_socket.set(zmq::sockopt::conflate, 1);
  web_control_pull_socket.bind("ipc://" + args.web_control_socket_path);

  // http://api.zeromq.org/3-0:zmq-poll
  // Can add multiple push pull sockets here. Useful for when front end is
  // integrated
  std::vector<zmq::pollitem_t> items = {
      {static_cast<void*>(pendant_pull_socket), 0, ZMQ_POLLIN, 0},
      {static_cast<void*>(web_control_pull_socket), 0, ZMQ_POLLIN, 0}};

  // Now the thread will just read in inputs. Another thread will act upon
  // them. All writes go through SharedGcsState under a single mutex.
  while (server_running) {
    zmq::poll(items, middleware_timing::COMMAND_LOOP_POLL);

    // Pendant Data
    if (items[0].revents & ZMQ_POLLIN) {
      zmq::message_t pendant_msg;
      zmq::recv_result_t pendant_result =
          pendant_pull_socket.recv(pendant_msg, zmq::recv_flags::none);
      if (pendant_result) {
        gcs_state.set_pendant_received(collect_pull_data(pendant_msg));
      }
    } else {
      gcs_state.pendant_no_data();
    }

    // Websocket data
    if (items[1].revents & ZMQ_POLLIN) {
      zmq::message_t web_control_msg;
      zmq::recv_result_t web_control_result =
          web_control_pull_socket.recv(web_control_msg, zmq::recv_flags::none);
      if (web_control_result) {
        gcs_state.set_websocket_received(collect_pull_data(web_control_msg));
      }
    }
  }

  try {
    // Cleanup
    // Do not cleanup `all_context` here.
    // Clean it up in main after all threads have closed
    pendant_pull_socket.close();
    web_control_pull_socket.close();
  } catch (const std::exception& e) {
    slogger::error("Error during cleanup");
    slogger::error(std::string(e.what()));
  }
}

std::vector<uint8_t> collect_pull_data(const zmq::message_t& last_pendant_msg) {
  return std::vector<uint8_t>(
      static_cast<const uint8_t*>(last_pendant_msg.data()),
      static_cast<const uint8_t*>(last_pendant_msg.data()) +
          last_pendant_msg.size());
}

std::vector<uint8_t> create_GCS_TO_AV_data(const bool BROADCAST,
                                           AvSequence& sequence) {
  std::vector<uint8_t> data;

  const bool camera_power = sequence.get_camera_power();

  data.push_back(0x01);  // Packet ID

  uint8_t byte1 = (0b101 << 5) | (camera_power << 4);
  data.push_back(byte1);

  uint8_t byte2 = (0b010 << 5) | ((!camera_power) << 4) | 0b1111;
  data.push_back(byte2);

  data.push_back(BROADCAST ? 0b10101010 : 0b00000000);

  return data;
}
