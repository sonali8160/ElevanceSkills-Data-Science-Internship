"""
Main Task 2 ticket workflow.

Conversation
    -> extraction
    -> missing information
    -> severity
    -> priority
    -> SLA
    -> routing
    -> duplicate detection
    -> grouping
    -> masked handoff
"""

from datetime import datetime
from typing import List

from .config import DEFAULT_SLA_MINUTES, SLA_WARNING_THRESHOLD
from .duplicate import detect_duplicate
from .extractor import extract_ticket_data
from .grouping import group_related_issues
from .handoff import generate_handoff_summary
from .missing_info import (
    build_information_request,
    get_missing_information,
)
from .models import (
    SLAConfig,
    SupportTicket,
    TicketWorkflowResult,
)
from .priority import (
    calculate_priority,
    derive_severity,
)
from .routing import route_ticket
from .sla import calculate_sla_status


def build_default_sla_config() -> SLAConfig:
    """
    Create the default runtime SLA configuration.
    """

    return SLAConfig(
        allowed_minutes=dict(
            DEFAULT_SLA_MINUTES
        ),
        warning_threshold=SLA_WARNING_THRESHOLD,
    )


def _conversation_start(messages):
    """
    Find first user-message timestamp.
    """

    user_messages = [
        message
        for message in messages
        if message.role.lower() == "user"
    ]

    if not user_messages:
        return datetime.now()

    return min(
        message.timestamp
        for message in user_messages
    )


def create_ticket_from_conversation(
    messages,
    ticket_id: str,
    current_time: datetime = None,
) -> SupportTicket:
    """
    Convert an unresolved conversation into a structured ticket.
    """

    if current_time is None:
        current_time = datetime.now()

    extracted = extract_ticket_data(
        messages
    )

    severity = derive_severity(
        risk_categories=extracted.risk_categories,
        urgent=extracted.urgent,
        frustrated=extracted.frustrated,
        sentiment=extracted.sentiment,
    )

    conversation_start = _conversation_start(
        messages
    )

    waiting_minutes = max(
        0.0,
        (
            current_time
            - conversation_start
        ).total_seconds()
        / 60.0,
    )

    priority, score = calculate_priority(
        severity=severity,
        sentiment=extracted.sentiment,
        waiting_minutes=waiting_minutes,
        customer_impact=extracted.customer_impact,
        sla_consumed_ratio=0.0,
        urgent=extracted.urgent,
        frustrated=extracted.frustrated,
    )

    ticket = SupportTicket(
        ticket_id=ticket_id,
        created_at=conversation_start,
        customer=extracted.customer,
        order_id=extracted.order_id,
        product=extracted.product,
        issue=extracted.issue or "Issue not provided.",
        issue_category=extracted.issue_category,
        evidence=extracted.evidence,
        sentiment=extracted.sentiment,
        frustrated=extracted.frustrated,
        urgent=extracted.urgent,
        sarcastic=extracted.sarcastic,
        risk_categories=extracted.risk_categories,
        customer_impact=extracted.customer_impact,
        severity=severity,
        priority=priority,
        priority_score=score,
    )

    return ticket


def process_unresolved_conversation(
    messages,
    ticket_id: str,
    agents=None,
    existing_tickets=None,
    current_time: datetime = None,
    sla_config: SLAConfig = None,
    resolved: bool = False,
) -> TicketWorkflowResult:
    """Run extraction, validation, SLA, routing, duplicate and grouping steps.

    Duplicate detection and SLA monitoring still run when mandatory details
    are missing. A normal incomplete ticket waits for the customer, while a
    high-risk or SLA-breached ticket can still be routed/escalated.
    """
    if current_time is None:
        current_time = datetime.now()
    agents = agents or []
    existing_tickets = existing_tickets or []
    sla_config = sla_config or build_default_sla_config()

    if resolved:
        return TicketWorkflowResult(
            ticket=None, missing_information=[], information_request=None,
            sla_status=None, routing=None, duplicate=None, groups=[],
            completed=False,
        )

    ticket = create_ticket_from_conversation(
        messages=messages, ticket_id=ticket_id, current_time=current_time,
    )
    missing = get_missing_information(ticket)
    ticket.missing_information = missing
    information_request = build_information_request(missing)
    if missing:
        ticket.status = "awaiting_customer_information"

    # Initial SLA estimate uses the severity-derived priority.
    sla_status = calculate_sla_status(
        created_at=ticket.created_at, current_time=current_time,
        priority=ticket.priority, config=sla_config,
    )

    # Priority uses SLA consumption too; then recompute SLA against the
    # resulting priority because each priority can have a different target.
    priority, score = calculate_priority(
        severity=ticket.severity,
        sentiment=ticket.sentiment,
        waiting_minutes=max(
            0.0,
            (current_time - ticket.created_at).total_seconds() / 60.0,
        ),
        customer_impact=ticket.customer_impact,
        sla_consumed_ratio=sla_status.consumed_ratio,
        urgent=ticket.urgent,
        frustrated=ticket.frustrated,
    )
    ticket.priority = priority
    ticket.priority_score = score
    sla_status = calculate_sla_status(
        created_at=ticket.created_at, current_time=current_time,
        priority=ticket.priority, config=sla_config,
    )

    # A warning/breach is a runtime condition, not a static creation-time flag.
    if sla_status.breached:
        ticket.sla_breached = True
        ticket.status = "sla_breached"
        ticket.escalation_triggered = True
        ticket.escalation_reason = (
            f"SLA breach: {sla_status.elapsed_business_minutes:.1f} business minutes "
            f"elapsed against {sla_status.allowed_minutes} allowed minutes."
        )
        ticket.escalation_timestamp = current_time
        ticket.escalation_queue = "sla_escalation"
        ticket.priority = "critical"
        ticket.priority_score = max(ticket.priority_score, 75.0)
        # Keep the SLA status/deadline consistent with the escalated priority.
        sla_status = calculate_sla_status(
            created_at=ticket.created_at, current_time=current_time,
            priority=ticket.priority, config=sla_config,
        )
        ticket.escalation_reason = (
            f"SLA breach: {sla_status.elapsed_business_minutes:.1f} business minutes "
            f"elapsed against {sla_status.allowed_minutes} allowed minutes."
        )
    elif sla_status.warning:
        ticket.sla_warning = True
        if not missing:
            ticket.status = "sla_warning"

    ticket.sla_warning = sla_status.warning
    ticket.sla_breached = sla_status.breached
    ticket.sla_consumed_ratio = sla_status.consumed_ratio
    ticket.sla_deadline = sla_status.deadline

    # High-risk categories escalate independently of sentiment and missing
    # information. A calm duplicate-payment/account-security/legal complaint
    # must not wait for evidence before the risk workflow starts.
    high_risk_categories = {
        "duplicate_payment", "account_compromise", "account_security",
        "legal_threat", "legal", "fraud", "unauthorized_transaction",
    }
    matched_risks = sorted(
        high_risk_categories.intersection(
            {str(value).strip().lower() for value in ticket.risk_categories}
        )
    )
    if matched_risks and not ticket.escalation_triggered:
        ticket.escalation_triggered = True
        ticket.escalation_timestamp = current_time
        ticket.escalation_reason = (
            "High-risk condition detected: " + ", ".join(matched_risks)
        )
        ticket.escalation_queue = "high_risk_escalation"

    # Always run duplicate detection, even if details are missing.
    duplicate = detect_duplicate(
        ticket=ticket, existing_tickets=existing_tickets,
        current_time=current_time,
    )
    if duplicate.is_duplicate:
        ticket.duplicate_of = duplicate.duplicate_ticket_id
        # Preserve breach status; duplicate linkage remains explicit.
        if not ticket.sla_breached:
            ticket.status = "duplicate"

    # Group related issues independently from duplicate detection.
    all_tickets = list(existing_tickets) + [ticket]
    groups = group_related_issues(all_tickets)
    for group in groups:
        if ticket.ticket_id in group.ticket_ids:
            ticket.related_ticket_ids = [
                item for item in group.ticket_ids if item != ticket.ticket_id
            ]

    # Normal tickets missing mandatory details wait for the customer.
    # High-risk tickets and SLA breaches still route to avoid unsafe delays.
    high_risk = bool(ticket.risk_categories) or ticket.severity == "critical"
    routing = None
    if not missing or high_risk or ticket.sla_breached:
        routing = route_ticket(
            ticket=ticket, agents=agents, current_time=current_time,
            config=sla_config,
        )
        ticket.assigned_agent = routing.assigned_agent
        ticket.assigned_queue = routing.assigned_queue

        # If an urgent/high-risk ticket has no qualified agent, preserve the
        # operational queue and explicitly invoke the supervisor fallback.
        if (
            ticket.escalation_triggered
            and not routing.assigned_agent
            and routing.assigned_queue in {"on_call", "unavailable_team"}
        ):
            ticket.escalation_queue = "supervisor_fallback"
            ticket.escalation_reason = (
                (ticket.escalation_reason or "High-risk ticket")
                + "; no qualified agent available, supervisor fallback required"
            )

    ticket.handoff_summary = generate_handoff_summary(
        ticket, sla_status, routing,
    )

    return TicketWorkflowResult(
        ticket=ticket,
        missing_information=missing,
        information_request=information_request,
        sla_status=sla_status,
        routing=routing,
        duplicate=duplicate,
        groups=groups,
        completed=not missing,
    )
