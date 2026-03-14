#include "server_args.hpp"

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
    if (argc >= 17 && std::string(argv[16]) == "--GSE_ONLY") {
      args.gse_only_mode = true;
    }
  } else {
    if (argc >= 8 && std::string(argv[7]) == "--GSE_ONLY") {
      args.gse_only_mode = true;
    }
  }

  return args;
}
