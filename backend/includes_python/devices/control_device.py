from abc import ABC, abstractmethod
from backend.includes_python.devices.pendant_state import PendantState
import backend.includes_python.process_logging as slogger
from backend.includes_python.timers import RepeatingTimer


class ControlDevice(ABC):
    def __init__(self):
        # DONT instantiate a ControlDevice manually
        # Use the get_control_device() function
        self._setup_device()
        # Set default fallback state to send whist waiting for inputs
        self.state_table = PendantState.get_fallback_table()
        self.previous_table = self.state_table
        # avoid spamming logs if something goes wrong
        self.complain_timer = RepeatingTimer(10)

    @abstractmethod
    def _setup_device(self) -> None:
        """Setup the control device"""
        pass

    @abstractmethod
    def _update_state_table(self) -> None:
        """Updates state table with new values"""
        pass

    def get_state_table(self) -> PendantState:
        """Updates and gets the current states from the control device."""
        try:
            self._update_state_table()
        except Exception as e:
            if self.complain_timer.time_has_passed():
                slogger.warning(f"Failed to update pendant states : {e}")

        if not self.state_table:
            slogger.warning(
                "No inputs received from control device, using fallback state"
            )
            self.state_table = PendantState.get_fallback_table()

        if self.state_table != self.previous_table:
            slogger.info(f"Pendant State changed to {repr(self.state_table)}")
            self.previous_table = self.state_table

        return self.state_table

    def cleanup(self) -> None:
        """Code to run after controller is no longer needed."""
        pass
