from backend.includes_python.timers import RepeatingTimer
import pytest
import time

EPSILON = 1e-3

def test_repeating_timer():
    timer = RepeatingTimer(0.01)

    # timer is supposed to retun true immidiently
    assert timer.time_has_passed()

    start_time = time.monotonic()

    while not timer.time_has_passed():
        pass

    time_passed = time.monotonic() - start_time
    
    # timer should return true again after the defined 0.01s
    assert abs(time_passed - 0.01) < EPSILON

    time.sleep(0.005)

    # wait for the timer to fully pass once after waiting a bit
    while not timer.time_has_passed():
        pass

    start_time = time.monotonic()

    while not timer.time_has_passed():
        pass

    time_passed = time.monotonic() - start_time
    
    # timer should return true again after the defined 0.01s even after being thrown off by 0.005s
    assert abs(time_passed - 0.01) < EPSILON

