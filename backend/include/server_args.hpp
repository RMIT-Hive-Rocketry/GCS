#pragma once

#include "subprocess_logging.hpp"
#include "uart_e5_interface.hpp"

struct ParsedArgs {
  std::string gse_type;
  std::string gse_path;
  std::string av_type;
  std::string av_path;
  std::string pendant_socket_path;
  std::string web_control_socket_path;
  LoraConfig lora_cfg;
  bool gse_only_mode;
};

ParsedArgs parse_args(int argc, char* argv[]);
