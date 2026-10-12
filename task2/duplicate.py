"""
Duplicate ticket detection.
"""

import re
from datetime import datetime
from difflib import SequenceMatcher

from .models import DuplicateResult, SupportTicket


def _normalize(text: str) -> str:
    """
    Normalize text for similarity comparison.
    """

    text = text.lower()

    text = re.sub(
        r"\b[\w.-]+@[\w.-]+\.\w+\b",
        " ",
        text,
    )

    text = re.sub(
        r"\d+",
        " ",
        text,
    )

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text,
    )

    return " ".join(text.split())


def _similarity(first: str, second: str) -> float:
    """
    Calculate text similarity.
    """

    first_normalized = _normalize(first)
    second_normalized = _normalize(second)

    if not first_normalized or not second_normalized:
        return 0.0

    sequence_score = SequenceMatcher(
        None,
        first_normalized,
        second_normalized,
    ).ratio()

    first_words = set(first_normalized.split())
    second_words = set(second_normalized.split())

    if not first_words or not second_words:
        return sequence_score

    intersection = len(
        first_words.intersection(second_words)
    )

    union = len(
        first_words.union(second_words)
    )

    jaccard_score = (
        intersection / union
        if union
        else 0.0
    )

    return (
        0.6 * sequence_score
        + 0.4 * jaccard_score
    )


def _normalize_identifier(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _same_customer(
    first: SupportTicket,
    second: SupportTicket,
) -> bool:
    first_email = first.customer.email
    second_email = second.customer.email

    if first_email and second_email:
        return (
            first_email.lower()
            == second_email.lower()
        )

    first_customer_id = first.customer.customer_id
    second_customer_id = second.customer.customer_id

    if first_customer_id and second_customer_id:
        return (
            first_customer_id.lower()
            == second_customer_id.lower()
        )

    first_name = first.customer.name
    second_name = second.customer.name

    if first_name and second_name:
        return (
            first_name.strip().lower()
            == second_name.strip().lower()
        )

    return False


def detect_duplicate(
    ticket: SupportTicket,
    existing_tickets,
    current_time: datetime = None,
    window_hours: int = 72,
) -> DuplicateResult:
    """
    Detect whether a ticket is a duplicate of an existing ticket.
    """

    best_match = None
    best_score = 0.0

    for existing in existing_tickets:

        if existing.ticket_id == ticket.ticket_id:
            continue

        # Time-window check.
        if current_time is not None:

            age_hours = (
                current_time
                - existing.created_at
            ).total_seconds() / 3600.0

            if age_hours < 0:
                continue

            if age_hours > window_hours:
                continue

        # Customer identity is preferred.
        same_customer = _same_customer(
            ticket,
            existing,
        )

        if not same_customer:
            # An exact order can still strongly indicate
            # the same request.
            if not (
                ticket.order_id
                and existing.order_id
                and _normalize_identifier(ticket.order_id)
                == _normalize_identifier(existing.order_id)
            ):
                continue

        # Different order IDs mean different requests.
        if (
            ticket.order_id
            and existing.order_id
            and _normalize_identifier(ticket.order_id)
            != _normalize_identifier(existing.order_id)
        ):
            continue

        # Different products should not automatically become duplicates.
        if (
            ticket.product
            and existing.product
            and ticket.product.lower()
            != existing.product.lower()
        ):
            continue

        score = _similarity(
            ticket.issue,
            existing.issue,
        )

        same_category = (
            ticket.issue_category == existing.issue_category
        )
        same_order = bool(
            ticket.order_id and existing.order_id
            and _normalize_identifier(ticket.order_id) == _normalize_identifier(existing.order_id)
        )
        same_product = bool(
            ticket.product and existing.product
            and ticket.product.strip().lower() == existing.product.strip().lower()
        )

        # Matching customer + same order + same issue category is strong
        # evidence even when the customer phrases the request differently.
        if same_category and same_order:
            threshold = 0.30
        elif same_category and same_product and same_customer:
            threshold = 0.45
        else:
            threshold = 0.55

        if score >= threshold and score > best_score:
            best_score = score
            best_match = existing

    if best_match is None:
        return DuplicateResult(
            is_duplicate=False,
            reason="No matching duplicate request found.",
        )

    return DuplicateResult(
        is_duplicate=True,
        duplicate_ticket_id=best_match.ticket_id,
        similarity=best_score,
        reason=(
            "The ticket matches an existing request from "
            "the same customer/order/product with sufficiently "
            "similar issue text."
        ),
    )