from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# ============================================================
# MESSAGE ANALYSIS
# ============================================================

@dataclass
class MessageAnalysis:

    language: str

    sentiment: str

    frustrated: bool

    urgent: bool

    sarcastic: bool

    confidence: Dict[str, float]

    risk_categories: List[str] = field(
        default_factory=list
    )

    # Used for response tone
    recommended_tone: str = "professional"


# ============================================================
# CONVERSATION MESSAGE
# ============================================================

@dataclass
class ConversationMessage:

    text: str

    timestamp: datetime

    role: str = "user"

    analysis: Optional[MessageAnalysis] = None


# ============================================================
# ESCALATION RESULT
# ============================================================

@dataclass
class EscalationResult:

    required: bool

    queue: Optional[str] = None

    reason: Optional[str] = None

    activated_conditions: List[str] = field(
        default_factory=list
    )

    conversation_summary: Optional[str] = None

    timestamp: Optional[datetime] = None

    scheduled_for: Optional[datetime] = None