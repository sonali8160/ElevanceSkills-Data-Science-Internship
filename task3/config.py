# task3/config.py

from types import SimpleNamespace
from datetime import time


# Retry delays required by Task 3
RETRY_DELAYS = [15, 30, 60]


# Configurable maintenance window
MAINTENANCE_START = time(2, 0)
MAINTENANCE_END = time(4, 0)


# Configurable update schedule
UPDATE_TIME = time(2, 0)


def create_schedule():
    return SimpleNamespace(
        maintenance_window=SimpleNamespace(
            start=MAINTENANCE_START,
            end=MAINTENANCE_END
        ),
        retry_delays_minutes=RETRY_DELAYS,
        update_time=UPDATE_TIME
    )


def in_maintenance_window(current_time):
    """Check the default window, including windows that cross midnight."""
    if MAINTENANCE_START < MAINTENANCE_END:
        return MAINTENANCE_START <= current_time < MAINTENANCE_END
    if MAINTENANCE_START > MAINTENANCE_END:
        return current_time >= MAINTENANCE_START or current_time < MAINTENANCE_END
    return False