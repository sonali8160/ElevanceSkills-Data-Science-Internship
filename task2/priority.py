"""
Ticket priority calculation.
"""

from typing import Tuple

from .config import PRIORITY_THRESHOLDS


def derive_severity(
    risk_categories,
    urgent: bool,
    frustrated: bool,
    sentiment: str,
) -> str:
    """
    Determine base severity.
    """

    high_risk = {
        "account_compromise",
        "duplicate_payment",
        "legal_threat",
    }

    if any(
        risk in high_risk
        for risk in risk_categories
    ):
        return "critical"

    if urgent:
        return "high"

    if frustrated and sentiment == "negative":
        return "high"

    if sentiment == "negative":
        return "medium"

    return "low"


def calculate_priority(
    severity: str,
    sentiment: str,
    waiting_minutes: float,
    customer_impact: str,
    sla_consumed_ratio: float = 0.0,
    urgent: bool = False,
    frustrated: bool = False,
) -> Tuple[str, float]:
    """
    Calculate priority using all required Task 2 factors.

    Returns:
        (priority, score)
    """

    severity_points = {
        "critical": 40,
        "high": 30,
        "medium": 20,
        "low": 10,
    }

    score = float(
        severity_points.get(
            severity,
            10,
        )
    )

    # Sentiment
    if sentiment == "negative":
        score += 15

    elif sentiment == "neutral":
        score += 5

    elif sentiment == "positive":
        score += 0

    # Frustration
    if frustrated:
        score += 10

    # Urgency
    if urgent:
        score += 15

    # Waiting time
    if waiting_minutes > 240:
        score += 15

    elif waiting_minutes > 60:
        score += 10

    elif waiting_minutes > 15:
        score += 5

    # Customer impact
    impact_points = {
        "individual": 0,
        "multiple": 10,
        "business": 20,
        "widespread": 25,
    }

    score += impact_points.get(
        customer_impact,
        0,
    )

    # SLA pressure
    if sla_consumed_ratio >= 1.0:
        score += 20

    elif sla_consumed_ratio >= 0.75:
        score += 10

    # Convert score to priority.
    if score >= PRIORITY_THRESHOLDS["critical"]:
        priority = "critical"

    elif score >= PRIORITY_THRESHOLDS["high"]:
        priority = "high"

    elif score >= PRIORITY_THRESHOLDS["medium"]:
        priority = "medium"

    else:
        priority = "low"

    return priority, score