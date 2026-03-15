#pragma once

#include <string>

struct WarningString {
  std::string color;
  std::string name;
};

static const WarningString GSE{"GSE", "\033[38;5;10m"};  // green
static const WarningString AV{"AV", "\033[38;5;205m"};   // pink
static const WarningString DAQ{"DAQ", "\033[38;5;1m"};   // red
