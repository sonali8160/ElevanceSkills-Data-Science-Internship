"""
Data models used by Task 2.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, time
from typing import Dict, List, Optional, Set


@dataclass
class CustomerDetails:
    """
    Customer information extracted from the conversation.
    """

    name: Optional[str] = None
    customer_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


@dataclass
class ExtractedTicketData:
    """
    Raw structured information extracted from a conversation.
    """

    customer: CustomerDetails = field(default_factory=CustomerDetails)
    order_id: Optional[str] = None
    product: Optional[str] = None
    issue: Optional[str] = None
    issue_category: str = "general"
    evidence: List[str] = field(default_factory=list)

    sentiment: str = "neutral"
    frustrated: bool = False
    urgent: bool = False
    sarcastic: bool = False
    risk_categories: List[str] = field(default_factory=list)

    customer_impact: str = "individual"


@dataclass
class SLAConfig:
    """
    Runtime-configurable SLA rules.
    """

    allowed_minutes: Dict[str, int] = field(default_factory=dict)

    warning_threshold: float = 0.75

    business_start: time = time(9, 0)
    business_end: time = time(18, 0)

    business_days: Set[int] = field(
        default_factory=lambda: {0, 1, 2, 3, 4}
    )

    holidays: Set[date] = field(default_factory=set)


@dataclass
class SLAStatus:
    """
    Current SLA state of a ticket.
    """

    priority: str
    allowed_minutes: int
    elapsed_business_minutes: float
    consumed_ratio: float
    warning: bool
    breached: bool
    deadline: datetime


@dataclass
class SupportTicket:
    """
    Final structured support ticket.
    """

    ticket_id: str
    created_at: datetime

    customer: CustomerDetails
    order_id: Optional[str]
    product: Optional[str]

    issue: str
    issue_category: str

    evidence: List[str]

    sentiment: str
    frustrated: bool
    urgent: bool
    sarcastic: bool

    risk_categories: List[str]

    customer_impact: str

    severity: str = "medium"
    priority: str = "medium"
    priority_score: float = 0.0

    status: str = "open"

    missing_information: List[str] = field(default_factory=list)

    assigned_agent: Optional[str] = None
    assigned_queue: Optional[str] = None

    duplicate_of: Optional[str] = None

    related_ticket_ids: List[str] = field(default_factory=list)

    sla_warning: bool = False
    sla_breached: bool = False
    sla_consumed_ratio: float = 0.0
    sla_deadline: Optional[datetime] = None

    # Explicit audit fields for automatic SLA escalation.
    escalation_triggered: bool = False
    escalation_reason: Optional[str] = None
    escalation_timestamp: Optional[datetime] = None
    escalation_queue: Optional[str] = None

    handoff_summary: Optional[str] = None


@dataclass
class Agent:
    """
    Support agent information.
    """

    name: str

    skills: Set[str]

    available: bool = True

    workload: int = 0

    max_workload: int = 10

    shift_start: time = time(9, 0)
    shift_end: time = time(18, 0)

    working_days: Set[int] = field(
        default_factory=lambda: {0, 1, 2, 3, 4}
    )

    on_call: bool = False


@dataclass
class RoutingResult:
    """
    Result of ticket routing.
    """

    assigned_agent: Optional[str] = None
    assigned_queue: Optional[str] = None

    reason: str = ""

    scheduled_for: Optional[datetime] = None


@dataclass
class DuplicateResult:
    """
    Duplicate detection result.
    """

    is_duplicate: bool = False

    duplicate_ticket_id: Optional[str] = None

    similarity: float = 0.0

    reason: str = ""


@dataclass
class IssueGroup:
    """
    Group of related tickets.
    """

    group_id: str

    ticket_ids: List[str] = field(default_factory=list)

    relationship: str = "related"


@dataclass
class TicketWorkflowResult:
    """
    Complete Task 2 workflow result.
    """

    ticket: Optional[SupportTicket]

    missing_information: List[str]

    information_request: Optional[str]

    sla_status: Optional[SLAStatus]

    routing: Optional[RoutingResult]

    duplicate: Optional[DuplicateResult]

    groups: List[IssueGroup]

    completed: bool