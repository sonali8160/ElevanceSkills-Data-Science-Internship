"""
Configuration for Task 2.

All important SLA and ticketing rules are kept configurable.
"""

from datetime import time


# -------------------------------------------------------------------
# Ticket mandatory information
# -------------------------------------------------------------------

MANDATORY_FIELDS = (
    "customer",
    "issue",
    "contact",
)


# Additional information requested depending on issue type.
CONDITIONAL_FIELDS = {
    "payment": ("order_id",),
    "duplicate_payment": ("order_id", "evidence"),
    "account_compromise": ("evidence",),
    "account_security": ("evidence",),
    "legal_threat": ("evidence",),
}


# -------------------------------------------------------------------
# Business hours
# -------------------------------------------------------------------

BUSINESS_START = time(9, 0)
BUSINESS_END = time(18, 0)

BUSINESS_DAYS = {0, 1, 2, 3, 4}  # Monday-Friday


# -------------------------------------------------------------------
# Default SLA in business minutes
# -------------------------------------------------------------------

DEFAULT_SLA_MINUTES = {
    "critical": 60,
    "high": 120,
    "medium": 480,
    "low": 1440,
}


# Warning is generated when this percentage is consumed.
SLA_WARNING_THRESHOLD = 0.75


# -------------------------------------------------------------------
# Duplicate detection
# -------------------------------------------------------------------

DUPLICATE_WINDOW_HOURS = 72


# -------------------------------------------------------------------
# Priority scoring
# -------------------------------------------------------------------

PRIORITY_THRESHOLDS = {
    "critical": 75,
    "high": 55,
    "medium": 30,
}


# -------------------------------------------------------------------
# General support skills
# -------------------------------------------------------------------

GENERAL_SUPPORT_SKILL = "general_support"