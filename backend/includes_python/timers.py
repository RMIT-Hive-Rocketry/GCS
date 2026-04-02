import time


class RepeatingTimer:
    """
    represents a timer which repeats every time_length_s
    will drift over time, meaning it will wait time_length_s after the previous function call that returned true
    """

    time_of_last_true: float
    time_length_s: float

    def __init__(self, time_length_s):
        self.time_of_last_true = -999999999
        self.time_length_s = time_length_s

    def time_has_passed(self) -> bool:
        """
        returns true if time_length_s have passed since it last returned true
        will always return true on its first call
        """
        current_time = time.monotonic()
        if current_time - self.time_of_last_true > self.time_length_s:
            self.time_of_last_true = current_time
            return True
        return False
