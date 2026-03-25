from abc import ABC, abstractmethod
from backend.includes_python.devices.state_table import StateTable
import backend.includes_python.process_logging as slogger

# i thought of making this more abstract (PygameControlDevice etc)
# but I dont think its a good idea because if we ever need to make changes like adding a dial etc it will be a nighmare

class ControlDevice(ABC):
    def __init__(self):
        # DONT instanciate a ControlDevice manually
        # Use the get_control_device() funciton
        self._setup_device()
        # Set default fallback state to send whist waiting for inputs
        self.state_table = StateTable.get_fallback_table()

    @abstractmethod
    def _setup_device(self):
        """Setup the control device"""
        pass

    @abstractmethod
    def _update_state_table(self) -> None:
        """Updates state table with new values"""
        pass

    def get_state_table(self) -> StateTable:
        """Updates and gets the current states from the control device."""
        try:
            self._update_state_table()
        except Exception as e:
            slogger.warning(f"Failed to update pendant states : {e}")

        if not self.state_table:
            slogger.warning(
                "No inputs received from control device, using fallback state"
            )
            self.state_table = StateTable.get_fallback_table()
        return self.state_table

    def get_states_dict(self) -> dict:
        state_table = self.get_state_table()
        return state_table.get_states_dict()

    def cleanup(self):
        """Code to run after controller is no longer needed."""
        pass
