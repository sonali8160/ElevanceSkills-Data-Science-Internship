"""
Masked support handoff summary.
"""

import re

from .models import SupportTicket, SLAStatus, RoutingResult


EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?\d[\d\s().-]{8,}\d)(?!\d)"
)

CARD_PATTERN = re.compile(
    r"(?<!\d)\d{13,19}(?!\d)"
)


def mask_sensitive_data(text: str) -> str:
    """
    Mask sensitive personal/payment information.
    """

    text = EMAIL_PATTERN.sub(
        "[EMAIL]",
        text,
    )

    text = PHONE_PATTERN.sub(
        "[PHONE]",
        text,
    )

    text = CARD_PATTERN.sub(
        "[CARD]",
        text,
    )

    return text


def _masked_customer(ticket: SupportTicket) -> str:
    if ticket.customer.name:
        return "[CUSTOMER]"

    if ticket.customer.customer_id:
        return "[CUSTOMER_ID]"

    return "[CUSTOMER]"


def generate_handoff_summary(
    ticket: SupportTicket,
    sla_status: SLAStatus = None,
    routing: RoutingResult = None,
) -> str:
    """
    Generate a concise masked summary for another support agent/team.
    """

    def mask_ticket_identifiers(value: str) -> str:
        value = mask_sensitive_data(value)
        # Mask identifiers known from the structured ticket as well, in case
        # they were repeated in the issue text or evidence description.
        known_values = [ticket.customer.name, ticket.customer.customer_id,
                        ticket.customer.email, ticket.customer.phone]
        for known in known_values:
            if known:
                value = re.sub(re.escape(str(known)), "[CUSTOMER]", value,
                               flags=re.IGNORECASE)
        return value

    issue = mask_ticket_identifiers(ticket.issue)

    evidence = [
        mask_ticket_identifiers(item)
        for item in ticket.evidence
    ]

    evidence_text = (
        ", ".join(evidence)
        if evidence
        else "No evidence supplied"
    )

    routing_text = "Not assigned"

    if routing:
        if routing.assigned_agent:
            routing_text = (
                f"{routing.assigned_agent} "
                f"({routing.assigned_queue})"
            )
        elif routing.assigned_queue:
            routing_text = routing.assigned_queue

    if sla_status:
        sla_text = (
            f"{sla_status.elapsed_business_minutes:.1f}/"
            f"{sla_status.allowed_minutes:.1f} business minutes "
            f"({sla_status.consumed_ratio * 100:.1f}%)"
        )

        if sla_status.breached:
            sla_state = "BREACHED"

        elif sla_status.warning:
            sla_state = "WARNING"

        else:
            sla_state = "WITHIN SLA"

        sla_text += f" - {sla_state}"

    else:
        sla_text = "SLA not calculated"

    summary = (
        f"Ticket: {ticket.ticket_id}\n"
        f"Customer: {_masked_customer(ticket)}\n"
        f"Order: {ticket.order_id or 'Not provided'}\n"
        f"Product: {ticket.product or 'Not provided'}\n"
        f"Issue category: {ticket.issue_category}\n"
        f"Issue: {issue}\n"
        f"Evidence: {evidence_text}\n"
        f"Sentiment: {ticket.sentiment}\n"
        f"Severity: {ticket.severity}\n"
        f"Priority: {ticket.priority}\n"
        f"Customer impact: {ticket.customer_impact}\n"
        f"Risk: "
        f"{', '.join(ticket.risk_categories) or 'None'}\n"
        f"Routing: {routing_text}\n"
        f"SLA: {sla_text}\n"
        f"Status: {ticket.status}\n"
        f"Escalation triggered: {'Yes' if ticket.escalation_triggered else 'No'}\n"
        f"Escalation reason: {ticket.escalation_reason or 'None'}\n"
        f"Escalation queue: {ticket.escalation_queue or 'None'}"
    )

    return mask_sensitive_data(summary)