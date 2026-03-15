#include "server_args.hpp"

#include <utility>
#include <vector>

namespace {

/// Single source of truth for supported (GSE, AV) interface combinations.
/// Add or remove pairs here when support changes.
/// Interface names from start_middleware.py --> class InterfaceType(enum.Enum):
const std::vector<std::pair<std::string, std::string>>
    // GSE, AV
    SUPPORTED_INTERFACE_PAIRS = {
        {"TCP", "UART_E5"},
        {"TEST_UART_E5", "TEST_UART_E5"},
        {"TEST", "TEST"},
};

bool has_interface_support(const ParsedArgs& args) {
  for (const auto& [gse, av] : SUPPORTED_INTERFACE_PAIRS) {
    if (args.gse_type == gse && (args.gse_only_mode || args.av_type == av)) {
      return true;
    }
  }
  return false;
}

void require_interface_support(const ParsedArgs& args) {
  if (has_interface_support(args)) {
    return;
  }
  std::string msg =
      "Unsupported interface combination whilst GSE only mode is: " +
      std::to_string(args.gse_only_mode) + ": GSE=" + args.gse_type +
      ", AV=" + args.av_type + ". Supported combinations: ";
  const char* sep = "";
  for (const auto& [gse, av] : SUPPORTED_INTERFACE_PAIRS) {
    msg += sep;
    msg += "(GSE=" + gse + ", AV=" + av + ")";
    sep = "; ";
  }
  msg += ".";
  throw std::runtime_error(msg);
}

}  // namespace

ParsedArgs parse_args(int argc, char* argv[]) {
  // Argv: <gse_type> <gse_path> <av_type> <av_path> <pendant> <web>
  //       [9x lora if gse_type==UART_E5] [--GSE_ONLY]
  // Validation is done on the Python side; C++ only parses.
  const int MIN_ARGS = 7;
  if (argc < MIN_ARGS) {
    slogger::error("Not enough arguments.");
    slogger::error(
        "Usage: ./file <gse_type> <gse_path> <av_type> <av_path> "
        "<pendant socket path> <web control socket path> "
        "[lora params if gse_type=UART_E5] [--GSE_ONLY]");
    throw std::runtime_error("Error: Not enough arguments provided");
  }

  ParsedArgs args{.gse_type = argv[1],
                  .gse_path = argv[2],
                  .av_type = argv[3],
                  .av_path = argv[4],
                  .pendant_socket_path = argv[5],
                  .web_control_socket_path = argv[6],
                  .lora_cfg = {},
                  .gse_only_mode = false};

  // Parse --GSE_ONLY before interface check so GSE-only mode is allowed.
  if (args.gse_type == "UART_E5") {
    if (argc >= 17 && std::string(argv[16]) == "--GSE_ONLY") {
      args.gse_only_mode = true;
    }
  } else {
    if (argc >= 8 && std::string(argv[7]) == "--GSE_ONLY") {
      args.gse_only_mode = true;
    }
  }

  require_interface_support(args);

  if (args.gse_type == "UART_E5") {
    const int UART_ARGS = 9;
    if (argc < MIN_ARGS + UART_ARGS) {
      slogger::error("UART_E5 GSE requires 9 lora args after the 6 base args.");
      throw std::runtime_error("Error: Not enough arguments for UART_E5");
    }
    args.lora_cfg = {
        .frequency = argv[7],
        .spread_factor = argv[8],
        .bandwidth = argv[9],
        .tx_preamble = argv[10],
        .rx_preamble = argv[11],
        .power = argv[12],
        .crc = argv[13],
        .iq = argv[14],
        .net = argv[15],
    };
  }

  return args;
}
