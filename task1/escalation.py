"""
Task 1 - Escalation Engine

Requirements:
- High-risk escalation
- Account compromise
- Duplicate payment
- Legal threats
- Calm high-risk complaints
- Repeated negative messages
- Negative unresolved > 15 minutes
- Urgent after-hours on-call queue
- Normal after-hours next-working-day scheduling
- Business-hours priority support
- Escalation reason
- Activated condition
- Conversation summary
- Simulated time
"""

from datetime import datetime, time, timedelta
from typing import List, Optional

from . import config
from .analyzer import analyze_message
from .models import (
    ConversationMessage,
    EscalationResult,
)


# ============================================================
# CONFIGURATION
# ============================================================

def _get_business_start() -> time:

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


def _get_business_end() -> time:

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


def _get_business_days():

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


def _get_negative_threshold() -> int:

    value = getattr(
        config,
        "NEGATIVE_ESCALATION_MINUTES",
        15,
    )

    try:
        return int(value)
    except (TypeError, ValueError):
        return 15


def _get_repeated_threshold() -> int:

    value = getattr(
        config,
        "REPEATED_NEGATIVE_THRESHOLD",
        3,
    )

    try:
        return int(value)
    except (TypeError, ValueError):
        return 3


# ============================================================
# TIME
# ============================================================

def is_business_hours(
    current_time: datetime,
) -> bool:

    if current_time.weekday() not in _get_business_days():
        return False

    start = _get_business_start()
    end = _get_business_end()

    return (
        start
        <= current_time.time()
        < end
    )


def next_working_day(
    current_time: datetime,
) -> datetime:

    candidate = current_time + timedelta(days=1)

    while (
        candidate.weekday()
        not in _get_business_days()
    ):
        candidate += timedelta(days=1)

    return candidate.replace(
        hour=_get_business_start().hour,
        minute=_get_business_start().minute,
        second=0,
        microsecond=0,
    )


# ============================================================
# MESSAGE HELPERS
# ============================================================

def _user_messages(
    messages: List[ConversationMessage],
) -> List[ConversationMessage]:

    return [
        message
        for message in messages
        if str(message.role).lower() == "user"
    ]


def create_conversation_summary(
    messages: List[ConversationMessage],
) -> str:

    user_messages = _user_messages(messages)

    if not user_messages:
        return "No customer message available."

    parts = []

    for message in user_messages[-5:]:

        text = str(message.text).strip()

        if text:
            parts.append(text)

    return " | ".join(parts)


# ============================================================
# COMPLAINT DETECTION
# ============================================================

def is_complaint(analysis) -> bool:

    return (
        analysis.sentiment == "negative"
        or analysis.frustrated
        or analysis.urgent
        or bool(analysis.risk_categories)
    )


def _is_normal_service_complaint(
    text: str,
) -> bool:

    """
    Detect normal support complaints that may not contain
    an explicit negative sentiment word.

    Example:
        "My course certificate has not arrived."
    """

    normalized = text.lower().strip()

    complaint_patterns = [

        "not arrived",
        "has not arrived",
        "hasn't arrived",

        "not received",
        "has not received",
        "hasn't received",

        "still waiting",
        "waiting for",

        "not working",
        "doesn't work",
        "didn't work",

        "unable to",
        "cannot",
        "can't",

        "missing",
        "delayed",
        "delay",
        "late",

        "failed",
        "failure",

        "problem",
        "issue",

        "please check",
        "please help",
    ]

    return any(
        pattern in normalized
        for pattern in complaint_patterns
    )


# ============================================================
# ANALYSIS
# ============================================================

def _analyze_messages(
    messages: List[ConversationMessage],
):

    results = []

    for message in _user_messages(messages):

        if message.analysis is not None:

            results.append(
                message.analysis
            )

        else:

            results.append(
                analyze_message(
                    message.text
                )
            )

    return results


# ============================================================
# RISK CONDITIONS
# ============================================================

def _get_high_risk_conditions(
    analyses,
) -> List[str]:

    conditions = []

    for analysis in analyses:

        for category in analysis.risk_categories:

            if category not in conditions:
                conditions.append(category)

    return conditions


# ============================================================
# NEGATIVE COUNT
# ============================================================

def _count_negative_messages(
    analyses,
) -> int:

    count = 0

    for analysis in analyses:

        if (
            analysis.sentiment == "negative"
            or analysis.frustrated
        ):
            count += 1

    return count


# ============================================================
# DURATION
# ============================================================

def _conversation_duration_minutes(
    messages: List[ConversationMessage],
    current_time: datetime,
) -> float:

    user_messages = _user_messages(messages)

    if not user_messages:
        return 0.0

    first_timestamp = min(
        message.timestamp
        for message in user_messages
    )

    elapsed = (
        current_time - first_timestamp
    ).total_seconds() / 60.0

    return max(0.0, elapsed)




def _negative_duration_minutes(
    messages: List[ConversationMessage],
    current_time: datetime,
) -> float:
    """Measure unresolved duration from the first negative user message."""
    negative_timestamps = []

    for message in _user_messages(messages):
        analysis = message.analysis or analyze_message(message.text)

        if analysis.sentiment == "negative" or analysis.frustrated:
            negative_timestamps.append(message.timestamp)

    if not negative_timestamps:
        return 0.0

    elapsed = (
        current_time - min(negative_timestamps)
    ).total_seconds() / 60.0

    return max(0.0, elapsed)


# ============================================================
# MAIN ESCALATION
# ============================================================

def evaluate_escalation(
    messages: List[ConversationMessage],
    current_time: Optional[datetime] = None,
    resolved: bool = False,
) -> EscalationResult:

    if current_time is None:
        current_time = datetime.now()

    user_messages = _user_messages(messages)

    # --------------------------------------------------------
    # No customer message
    # --------------------------------------------------------

    if not user_messages:

        return EscalationResult(
            required=False,
            timestamp=current_time,
        )

    # --------------------------------------------------------
    # Resolved
    # --------------------------------------------------------

    if resolved:

        return EscalationResult(
            required=False,
            timestamp=current_time,
            conversation_summary=(
                create_conversation_summary(
                    messages
                )
            ),
        )

    # --------------------------------------------------------
    # Analyze
    # --------------------------------------------------------

    analyses = _analyze_messages(messages)

    high_risk_conditions = (
        _get_high_risk_conditions(
            analyses
        )
    )

    negative_count = (
        _count_negative_messages(
            analyses
        )
    )

    # The 15-minute clock starts when the negative issue first appears,
    # not when an earlier neutral message started the conversation.
    negative_duration_minutes = (
        _negative_duration_minutes(
            messages,
            current_time,
        )
    )

    # --------------------------------------------------------
    # Urgency
    # --------------------------------------------------------

    urgent_detected = any(
        analysis.urgent
        for analysis in analyses
    )

    # --------------------------------------------------------
    # Normal service complaint
    # --------------------------------------------------------

    normal_complaint_detected = any(
        _is_normal_service_complaint(
            message.text
        )
        for message in user_messages
    )

    complaint_detected = (
        any(
            is_complaint(analysis)
            for analysis in analyses
        )
        or normal_complaint_detected
    )

    # --------------------------------------------------------
    # CONDITIONS
    # --------------------------------------------------------

    activated_conditions = []

    # High-risk condition
    for condition in high_risk_conditions:

        condition_name = (
            "high_risk:"
            + condition
        )

        if condition_name not in activated_conditions:

            activated_conditions.append(
                condition_name
            )

    # Repeated negative
    repeated_negative = (
        negative_count
        >= _get_repeated_threshold()
    )

    if repeated_negative:

        activated_conditions.append(
            "repeated_negative_messages"
        )

    # Negative unresolved > 15 minutes
    negative_unresolved = (
        negative_count > 0
        and negative_duration_minutes
        > _get_negative_threshold()
    )

    if negative_unresolved:

        activated_conditions.append(
            "negative_unresolved_15_minutes"
        )

    # --------------------------------------------------------
    # After-hours conditions
    # --------------------------------------------------------

    after_hours = not is_business_hours(
        current_time
    )

    after_hours_urgent = (
        after_hours
        and (
            urgent_detected
            or bool(high_risk_conditions)
        )
    )

    after_hours_normal = (
        after_hours
        and complaint_detected
        and not after_hours_urgent
    )

    if after_hours_urgent:

        activated_conditions.append(
            "after_hours_urgent"
        )

    elif after_hours_normal:

        activated_conditions.append(
            "after_hours_normal_complaint"
        )

    # --------------------------------------------------------
    # Normal urgent condition
    # --------------------------------------------------------

    if urgent_detected and not after_hours:

        activated_conditions.append(
            "urgent_complaint"
        )

    # --------------------------------------------------------
    # SHOULD ESCALATE?
    # --------------------------------------------------------

    required = (
        bool(high_risk_conditions)
        or repeated_negative
        or negative_unresolved
        or urgent_detected
        or after_hours_normal
    )

    # --------------------------------------------------------
    # No escalation
    # --------------------------------------------------------

    if not required:

        return EscalationResult(
            required=False,
            timestamp=current_time,
            conversation_summary=(
                create_conversation_summary(
                    messages
                )
            ),
        )

    # --------------------------------------------------------
    # REASON
    # --------------------------------------------------------

    reasons = []

    if high_risk_conditions:

        risks = ", ".join(
            high_risk_conditions
        )

        reasons.append(
            "High-risk issue detected: "
            + risks
        )

    if repeated_negative:

        reasons.append(
            "Repeated negative messages detected"
        )

    if negative_unresolved:

        reasons.append(
            "Negative conversation unresolved "
            "for more than "
            + str(_get_negative_threshold())
            + " minutes"
        )

    if urgent_detected:

        reasons.append(
            "Urgent complaint detected"
        )

    if after_hours_normal:

        reasons.append(
            "Normal complaint received outside business hours"
        )

    reason = "; ".join(reasons)

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary = create_conversation_summary(
        messages
    )

    # --------------------------------------------------------
    # ROUTING
    # --------------------------------------------------------

    if after_hours_urgent:

        queue = "on_call"
        scheduled_for = None

    elif after_hours_normal:

        queue = "next_working_day"
        scheduled_for = next_working_day(
            current_time
        )

    else:

        queue = "priority_support"
        scheduled_for = None

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return EscalationResult(
        required=True,
        queue=queue,
        reason=reason,
        activated_conditions=(
            activated_conditions
        ),
        conversation_summary=summary,
        timestamp=current_time,
        scheduled_for=scheduled_for,
    )


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def check_escalation(
    messages: List[ConversationMessage],
    current_time: Optional[datetime] = None,
    resolved: bool = False,
) -> EscalationResult:

    return evaluate_escalation(
        messages=messages,
        current_time=current_time,
        resolved=resolved,
    )


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    now = datetime(
        2026,
        10,
        6,
        11,
        0,
    )

    message = ConversationMessage(
        text=(
            "Hello, I noticed an unauthorized "
            "transaction on my account."
        ),
        timestamp=now,
        role="user",
    )

    result = evaluate_escalation(
        messages=[message],
        current_time=now,
    )

    print("=" * 70)
    print("TASK 1 ESCALATION TEST")
    print("=" * 70)
    print("Required:", result.required)
    print("Queue:", result.queue)
    print("Reason:", result.reason)
    print(
        "Activated conditions:",
        result.activated_conditions,
    )
    print(
        "Summary:",
        result.conversation_summary,
    )