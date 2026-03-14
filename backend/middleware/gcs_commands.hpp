#pragma once

#include <vector>
#include <zmq.hpp>

class Sequence;

/// Copy ZMQ message bytes into a vector (for pendant or web control data).
std::vector<uint8_t> collect_pull_data(const zmq::message_t& last_pendant_msg);

/// Build GCS→AV command payload: packet ID, camera power bytes, broadcast flag.
std::vector<uint8_t> create_GCS_TO_AV_data(const bool BROADCAST,
                                           Sequence& sequence);
