from abc import ABC, abstractmethod
from backend.includes_python.devices.pendant_state import PendantState, GSEState
import backend.includes_python.process_logging as slogger
from typing import Dict


class ControlDevice(ABC):
    def __init__(self):
        # DONT instanciate a ControlDevice manually
        # Use the get_control_device() funciton
        self._setup_device()
        # Set default fallback state to send whist waiting for inputs
        self.state_table = PendantState.get_fallback_table()

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
            slogger.warning(f"Failed to update pendant states : {e}")

        if not self.state_table:
            slogger.warning(
                "No inputs received from control device, using fallback state"
            )
            self.state_table = PendantState.get_fallback_table()
        return self.state_table

    def cleanup(self) -> None:
        """Code to run after controller is no longer needed."""
        pass
