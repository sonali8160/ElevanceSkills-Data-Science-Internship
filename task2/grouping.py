"""
Related/unrelated ticket grouping.
"""

import re
from difflib import SequenceMatcher

from .models import IssueGroup, SupportTicket


def _tokens(text: str):
    cleaned = re.sub(
        r"[^a-zA-Z0-9\s]",
        " ",
        text.lower(),
    )

    return set(cleaned.split())


def _issue_similarity(
    first: str,
    second: str,
) -> float:
    first_tokens = _tokens(first)
    second_tokens = _tokens(second)

    if not first_tokens or not second_tokens:
        return 0.0

    intersection = len(
        first_tokens.intersection(second_tokens)
    )

    union = len(
        first_tokens.union(second_tokens)
    )

    jaccard = (
        intersection / union
        if union
        else 0.0
    )

    sequence = SequenceMatcher(
        None,
        first.lower(),
        second.lower(),
    ).ratio()

    return (
        0.6 * jaccard
        + 0.4 * sequence
    )


def _same_customer(
    first: SupportTicket,
    second: SupportTicket,
) -> bool:
    if (
        first.customer.email
        and second.customer.email
    ):
        return (
            first.customer.email.lower()
            == second.customer.email.lower()
        )

    if (
        first.customer.customer_id
        and second.customer.customer_id
    ):
        return (
            first.customer.customer_id.lower()
            == second.customer.customer_id.lower()
        )

    if (
        first.customer.name
        and second.customer.name
    ):
        return (
            first.customer.name.lower().strip()
            == second.customer.name.lower().strip()
        )

    return False


def issues_are_related(
    first: SupportTicket,
    second: SupportTicket,
) -> bool:
    """Identify related incidents without merging different issue types.

    Same-customer/order matches use a lower similarity threshold. Similar
    incidents from different customers can also be grouped when they share
    a category and product (or have very strong issue-text similarity), which
    helps surface a possible wider service incident.
    """
    if first.issue_category != second.issue_category:
        return False

    same_customer = _same_customer(first, second)

    if (
        same_customer
        and first.order_id
        and second.order_id
        and first.order_id.lower() == second.order_id.lower()
    ):
        return True

    similarity = _issue_similarity(first.issue, second.issue)

    if same_customer:
        if (
            first.product and second.product
            and first.product.lower() == second.product.lower()
            and similarity >= 0.35
        ):
            return True
        return similarity >= 0.70

    # Cross-customer grouping is intended for shared product/service incidents,
    # not merely because two tickets use the same broad category.
    same_product = bool(
        first.product and second.product
        and first.product.strip().lower() == second.product.strip().lower()
    )
    if same_product and similarity >= 0.45:
        return True

    return similarity >= 0.82


def group_related_issues(
    tickets,
):
    """Return connected groups of related tickets.

    Connected-component grouping avoids splitting an incident when A relates
    to B and B relates to C even if A and C use different wording.
    """
    tickets = list(tickets)
    groups = []
    visited = set()
    group_number = 1

    for ticket in tickets:
        if ticket.ticket_id in visited:
            continue

        component = []
        queue = [ticket]
        visited.add(ticket.ticket_id)

        while queue:
            current = queue.pop(0)
            component.append(current.ticket_id)
            for candidate in tickets:
                if candidate.ticket_id in visited:
                    continue
                if issues_are_related(current, candidate):
                    visited.add(candidate.ticket_id)
                    queue.append(candidate)

        groups.append(IssueGroup(
            group_id=f"GRP-{group_number:04d}",
            ticket_ids=component,
            relationship="related" if len(component) > 1 else "standalone",
        ))
        group_number += 1

    return groups
