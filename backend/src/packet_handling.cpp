#include "packet_handling.hpp"

void post_process_av(AvSequence& sequence,
                     const common::FlightState FLIGHT_STATE) {
  sequence.received_av();
  if (FLIGHT_STATE == common::FlightState::LAUNCH) {
    sequence.current_state = AvSequence::ONCE_AV_DETERMINING_LAUNCH;
  }
  switch (FLIGHT_STATE) {
    case common::FlightState::OH_NO:
    case common::FlightState::PRE_FLIGHT_NO_FLIGHT_READY:
    case common::FlightState::PRE_FLIGHT_FLIGHT_READY:
      break;
    case common::FlightState::LAUNCH:
    case common::FlightState::COAST:
    case common::FlightState::APOGEE:
    case common::FlightState::DESCENT:
    case common::FlightState::LANDED:
      sequence.set_start_sending_broadcast_flag(true);
    default:
      break;
  }
}
