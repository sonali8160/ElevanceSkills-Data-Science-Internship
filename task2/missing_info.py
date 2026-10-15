"""
Missing information detection for Task 2.

This module identifies mandatory and conditionally required
information that is missing from a support ticket.
"""

from typing import List

from .config import CONDITIONAL_FIELDS, MANDATORY_FIELDS
from .models import SupportTicket


def _field_available(
    ticket: SupportTicket,
    field: str,
) -> bool:
    """
    Check whether a particular ticket field contains
    usable information.
    """

    if field == "customer":
        return bool(
            ticket.customer.name
            or ticket.customer.customer_id
        )

    if field == "contact":
        return bool(
            ticket.customer.email
            or ticket.customer.phone
        )

    if field == "issue":
        return bool(
            ticket.issue
            and ticket.issue.strip()
        )

    if field == "order_id":
        return bool(ticket.order_id)

    if field == "product":
        return bool(ticket.product)

    if field == "evidence":
        return bool(ticket.evidence)

    return False


def get_missing_information(
    ticket: SupportTicket,
) -> List[str]:
    """
    Return all mandatory and conditionally required
    fields that are missing.
    """

    missing = []

    # ---------------------------------------------------------------
    # Mandatory fields
    # ---------------------------------------------------------------

    for field in MANDATORY_FIELDS:

        if not _field_available(
            ticket,
            field,
        ):
            missing.append(field)

    # ---------------------------------------------------------------
    # Conditional fields
    # ---------------------------------------------------------------

    conditional_fields = CONDITIONAL_FIELDS.get(
        ticket.issue_category,
        (),
    )

    for field in conditional_fields:

        if not _field_available(
            ticket,
            field,
        ):
            if field not in missing:
                missing.append(field)

    return missing


def build_information_request(
    missing_fields: List[str],
) -> str:
    """
    Create a customer-facing message requesting
    missing information.
    """

    if not missing_fields:
        return ""

    field_labels = {
        "customer": "your name or customer ID",

        "contact": (
            "your email address or phone number"
        ),

        "issue": (
            "a clear description of the issue"
        ),

        "order_id": (
            "your order ID"
        ),

        "product": (
            "the affected product or course"
        ),

    }

    requested = []

    for field in missing_fields:

        requested.append(
            field_labels.get(
                field,
                field,
            )
        )

    if len(requested) == 1:

        requested_text = requested[0]

    elif len(requested) == 2:

        requested_text = (
            requested[0]
            + " and "
            + requested[1]
        )

    else:

        requested_text = (
            ", ".join(requested[:-1])
            + ", and "
            + requested[-1]
        )

    return (
        "To create and process your support ticket, "
        f"please provide {requested_text}."
    )


# -------------------------------------------------------------------
# Backward-compatible alias
# -------------------------------------------------------------------
#
# This allows the code to work even if another part of the project
# uses the name get_missing_mandatory_fields().
#

def get_missing_mandatory_fields(
    ticket: SupportTicket,
) -> List[str]:
    """
    Backward-compatible alias for
    get_missing_information().
    """

    return get_missing_information(ticket)
