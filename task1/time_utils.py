"""
Task 1 - Time Utilities
"""

from datetime import datetime, time, timedelta

from . import config


# ============================================================
# CONFIG
# ============================================================

def _business_start():

    value = getattr(
        config,
        "BUSINESS_START",
        None,
    )

    if value is None:
        value = getattr(
            config,
            "BUSINESS_HOURS_START",
            None,
        )

    if isinstance(value, time):
        return value

    if isinstance(value, str):

        try:
            return datetime.strptime(
                value,
                "%H:%M",
            ).time()
        except ValueError:
            pass

    return time(9, 0)


def _business_end():

    value = getattr(
        config,
        "BUSINESS_END",
        None,
    )

    if value is None:
        value = getattr(
            config,
            "BUSINESS_HOURS_END",
            None,
        )

    if isinstance(value, time):
        return value

    if isinstance(value, str):

        try:
            return datetime.strptime(
                value,
                "%H:%M",
            ).time()
        except ValueError:
            pass

    return time(18, 0)


def _business_days():

    value = getattr(
        config,
        "BUSINESS_DAYS",
        None,
    )

    if value is None:
        value = getattr(
            config,
            "WORKING_DAYS",
            None,
        )

    if value is None:
        return {0, 1, 2, 3, 4}

    return set(value)


# ============================================================
# BUSINESS HOURS
# ============================================================

def is_business_hours(
    current_time: datetime,
) -> bool:

    if current_time.weekday() not in _business_days():
        return False

    return (
        _business_start()
        <= current_time.time()
        < _business_end()
    )


# ============================================================
# NEXT WORKING DAY
# ============================================================

def next_working_day(
    current_time: datetime,
) -> datetime:

    candidate = current_time + timedelta(days=1)

    while (
        candidate.weekday()
        not in _business_days()
    ):
        candidate += timedelta(days=1)

    return candidate.replace(
        hour=_business_start().hour,
        minute=_business_start().minute,
        second=0,
        microsecond=0,
    )