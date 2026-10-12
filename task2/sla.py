"""
Business-time SLA engine for Task 2.
"""

from datetime import datetime, timedelta, time, date

from .models import SLAConfig, SLAStatus


def _is_business_day(
    current_date: date,
    config: SLAConfig,
) -> bool:
    return (
        current_date.weekday() in config.business_days
        and current_date not in config.holidays
    )


def _next_business_start(
    current: datetime,
    config: SLAConfig,
) -> datetime:
    """
    Return the next valid business-hour starting time.
    """

    current_date = current.date()

    while True:
        if not _is_business_day(
            current_date,
            config,
        ):
            current_date += timedelta(days=1)

            current = datetime.combine(
                current_date,
                config.business_start,
            )

            continue

        day_start = datetime.combine(
            current_date,
            config.business_start,
        )

        day_end = datetime.combine(
            current_date,
            config.business_end,
        )

        if current < day_start:
            return day_start

        if current >= day_end:
            current_date += timedelta(days=1)

            current = datetime.combine(
                current_date,
                config.business_start,
            )

            continue

        return current


def business_minutes_between(
    start: datetime,
    end: datetime,
    config: SLAConfig,
) -> float:
    """
    Calculate business minutes between two timestamps.

    Weekends, holidays, and outside-business-hours periods
    are excluded.
    """

    if end <= start:
        return 0.0

    total_minutes = 0.0

    current_date = start.date()

    while current_date <= end.date():

        if _is_business_day(
            current_date,
            config,
        ):
            day_start = datetime.combine(
                current_date,
                config.business_start,
            )

            day_end = datetime.combine(
                current_date,
                config.business_end,
            )

            interval_start = max(
                start,
                day_start,
            )

            interval_end = min(
                end,
                day_end,
            )

            if interval_end > interval_start:
                seconds = (
                    interval_end - interval_start
                ).total_seconds()

                total_minutes += seconds / 60.0

        current_date += timedelta(days=1)

    return total_minutes


def add_business_minutes(
    start: datetime,
    minutes: float,
    config: SLAConfig,
) -> datetime:
    """
    Add business minutes to a datetime while excluding
    weekends, holidays, and outside-business-hours periods.
    """

    if minutes <= 0:
        return _next_business_start(
            start,
            config,
        )

    current = _next_business_start(
        start,
        config,
    )

    remaining = float(minutes)

    while remaining > 0:

        current_date = current.date()

        day_end = datetime.combine(
            current_date,
            config.business_end,
        )

        available_minutes = (
            day_end - current
        ).total_seconds() / 60.0

        if remaining <= available_minutes:
            return current + timedelta(
                minutes=remaining
            )

        remaining -= available_minutes

        next_date = current_date + timedelta(
            days=1
        )

        current = datetime.combine(
            next_date,
            config.business_start,
        )

        current = _next_business_start(
            current,
            config,
        )

    return current


def calculate_sla_status(
    created_at: datetime,
    current_time: datetime,
    priority: str,
    config: SLAConfig,
) -> SLAStatus:
    """
    Calculate current SLA state.
    """

    allowed_minutes = config.allowed_minutes.get(
        priority
    )

    if allowed_minutes is None:
        allowed_minutes = config.allowed_minutes.get(
            "medium",
            480,
        )

    elapsed = business_minutes_between(
        created_at,
        current_time,
        config,
    )

    if allowed_minutes <= 0:
        consumed_ratio = 1.0

    else:
        consumed_ratio = (
            elapsed / allowed_minutes
        )

    warning = (
        consumed_ratio >= config.warning_threshold
        and consumed_ratio < 1.0
    )

    breached = consumed_ratio >= 1.0

    deadline = add_business_minutes(
        created_at,
        allowed_minutes,
        config,
    )

    return SLAStatus(
        priority=priority,
        allowed_minutes=allowed_minutes,
        elapsed_business_minutes=elapsed,
        consumed_ratio=consumed_ratio,
        warning=warning,
        breached=breached,
        deadline=deadline,
    )


def update_sla_rule(
    config: SLAConfig,
    priority: str,
    allowed_minutes: int,
) -> None:
    """
    Change an SLA rule at runtime.
    """

    if allowed_minutes <= 0:
        raise ValueError(
            "SLA minutes must be greater than zero."
        )

    config.allowed_minutes[
        priority
    ] = allowed_minutes


def add_holiday(
    config: SLAConfig,
    holiday: date,
) -> None:
    """
    Add a holiday at runtime.
    """

    config.holidays.add(holiday)


def remove_holiday(
    config: SLAConfig,
    holiday: date,
) -> None:
    """
    Remove a holiday at runtime.
    """

    config.holidays.discard(holiday)