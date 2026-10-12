"""
Ticket routing engine.
"""

from datetime import datetime, timedelta

from .config import GENERAL_SUPPORT_SKILL
from .models import (
    Agent,
    RoutingResult,
    SLAConfig,
    SupportTicket,
)


def _agent_is_working(
    agent: Agent,
    current_time: datetime,
) -> bool:
    """
    Check whether an agent is currently within their working schedule.
    """

    if current_time.weekday() not in agent.working_days:
        return False

    current_clock = current_time.time()

    return (
        agent.shift_start
        <= current_clock
        < agent.shift_end
    )


def _required_skills(
    ticket: SupportTicket,
):
    """
    Determine skills needed for the ticket.
    """

    skills = set()

    if ticket.issue_category == "payment":
        skills.add("payments")

    elif ticket.issue_category == "duplicate_payment":
        skills.add("payments")

    elif ticket.issue_category in {"account_security", "account_compromise"}:
        skills.add("security")

    elif ticket.issue_category in {"legal", "legal_threat"}:
        skills.add("legal")

    elif ticket.issue_category == "technical":
        skills.add("technical")

    elif ticket.issue_category == "course":
        skills.add("course_support")

    else:
        skills.add(GENERAL_SUPPORT_SKILL)

    return skills


def _next_business_day_start(
    current_time: datetime,
    config: SLAConfig,
) -> datetime:
    """Return the next opening time, including today's opening if not started."""
    same_day_is_business_day = (
        current_time.weekday() in config.business_days
        and current_time.date() not in config.holidays
    )
    if same_day_is_business_day and current_time.time() < config.business_start:
        return current_time.replace(
            hour=config.business_start.hour,
            minute=config.business_start.minute,
            second=0,
            microsecond=0,
        )

    candidate_date = current_time.date() + timedelta(days=1)
    while (
        candidate_date.weekday() not in config.business_days
        or candidate_date in config.holidays
    ):
        candidate_date += timedelta(days=1)

    return datetime.combine(candidate_date, config.business_start)


def route_ticket(
    ticket: SupportTicket,
    agents,
    current_time: datetime,
    config: SLAConfig,
) -> RoutingResult:
    """
    Route a ticket using skills, availability, workload and
    business hours.
    """

    required_skills = _required_skills(ticket)

    within_business_hours = (
        current_time.weekday()
        in config.business_days
        and current_time.date()
        not in config.holidays
        and config.business_start
        <= current_time.time()
        < config.business_end
    )

    # ---------------------------------------------------------------
    # During business hours
    # ---------------------------------------------------------------

    if within_business_hours:

        candidates = []

        for agent in agents:

            if not agent.available:
                continue

            if agent.workload >= agent.max_workload:
                continue

            if not _agent_is_working(
                agent,
                current_time,
            ):
                continue

            if not required_skills.intersection(
                agent.skills
            ):
                continue

            candidates.append(agent)

        if candidates:

            # Lowest workload first.
            # Exact skill match gets preference.
            candidates.sort(
                key=lambda agent: (
                    0
                    if required_skills.issubset(
                        agent.skills
                    )
                    else 1,
                    agent.workload,
                    agent.name,
                )
            )

            selected = candidates[0]

            return RoutingResult(
                assigned_agent=selected.name,
                assigned_queue="assigned",
                reason=(
                    "Assigned to an available agent "
                    "with the required skill and capacity."
                ),
            )

        return RoutingResult(
            assigned_queue="unavailable_team",
            reason=(
                "No available qualified agent currently "
                "has the required skill and workload capacity."
            ),
        )

    # ---------------------------------------------------------------
    # After business hours
    # ---------------------------------------------------------------

    if ticket.urgent or ticket.priority == "critical":

        on_call_candidates = []

        for agent in agents:

            if not agent.available:
                continue

            if not agent.on_call:
                continue

            if agent.workload >= agent.max_workload:
                continue

            if not required_skills.intersection(
                agent.skills
            ):
                continue

            on_call_candidates.append(agent)

        if on_call_candidates:

            on_call_candidates.sort(
                key=lambda agent: (
                    agent.workload,
                    agent.name,
                )
            )

            selected = on_call_candidates[0]

            return RoutingResult(
                assigned_agent=selected.name,
                assigned_queue="on_call",
                reason=(
                    "Urgent or critical after-hours ticket "
                    "routed to an available on-call agent."
                ),
            )

        return RoutingResult(
            assigned_queue="on_call",
            reason=(
                "Urgent after-hours ticket requires on-call "
                "handling, but no qualified on-call agent is available."
            ),
        )

    # Normal after-hours request.
    return RoutingResult(
        assigned_queue="next_working_day",
        reason=(
            "Normal ticket received outside business hours; "
            "scheduled for the next working day."
        ),
        scheduled_for=_next_business_day_start(
            current_time,
            config,
        ),
    )