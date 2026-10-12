from datetime import time


# ============================================================
# BUSINESS HOURS
# ============================================================

BUSINESS_START = time(9, 0)
BUSINESS_END = time(18, 0)

# Monday = 0
# Tuesday = 1
# Wednesday = 2
# Thursday = 3
# Friday = 4
BUSINESS_DAYS = {0, 1, 2, 3, 4}


# ============================================================
# ESCALATION CONFIGURATION
# ============================================================

NEGATIVE_ESCALATION_MINUTES = 15

REPEATED_NEGATIVE_THRESHOLD = 3


# ============================================================
# HIGH-RISK CATEGORIES
# ============================================================

HIGH_RISK_CATEGORIES = {
    "account_compromise",
    "duplicate_payment",
    "legal_threat",
}


# ============================================================
# SUPPORTED LANGUAGES
# ============================================================

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
    "es": "Spanish",
    "fr": "French",
}


# ============================================================
# RESPONSE TONES
# ============================================================

RESPONSE_TONES = {
    "positive": "friendly",
    "neutral": "professional",
    "negative": "empathetic",
    "frustrated": "calming",
    "urgent": "direct_and_reassuring",
    "sarcastic": "calm_and_professional",
}