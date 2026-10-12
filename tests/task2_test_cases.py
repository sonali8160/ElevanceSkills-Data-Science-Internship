"""
Task 2 validation tests.

Run from:
customer_service_chatbot_LLM/

Command:
    python tests/task2_test_cases.py
"""

import sys
from datetime import datetime, date, time

sys.path.insert(
    0,
    ".",
)

from task1.models import ConversationMessage

from task2.models import (
    Agent,
    CustomerDetails,
    SLAConfig,
    SupportTicket,
)

from task2.extractor import extract_ticket_data

from task2.missing_info import (
    get_missing_information,
    build_information_request,
)

from task2.priority import (
    calculate_priority,
    derive_severity,
)

from task2.sla import (
    business_minutes_between,
    calculate_sla_status,
    update_sla_rule,
    add_holiday,
)

from task2.routing import route_ticket

from task2.duplicate import detect_duplicate

from task2.grouping import (
    issues_are_related,
    group_related_issues,
)

from task2.handoff import (
    generate_handoff_summary,
)

from task2.ticket_workflow import (
    process_unresolved_conversation,
    build_default_sla_config,
)


passed = 0
failed = 0


def check(name, condition):
    global passed, failed

    if condition:
        print(f"PASS: {name}")
        passed += 1
    else:
        print(f"FAIL: {name}")
        failed += 1


# -------------------------------------------------------------------
# Test 1: Extraction
# -------------------------------------------------------------------

messages = [
    ConversationMessage(
        text=(
            "My name is Rahul Sharma. "
            "Customer ID CUST123. "
            "My order ID is ORD456. "
            "The product is Python. "
            "I paid twice and I am very frustrated. "
            "My email is rahul@example.com. "
            "Screenshot attached."
        ),
        timestamp=datetime(2026, 9, 14, 10, 0),
        role="user",
    )
]

extracted = extract_ticket_data(
    messages
)

check(
    "Customer name extracted",
    extracted.customer.name == "Rahul Sharma",
)

check(
    "Customer ID extracted",
    extracted.customer.customer_id == "CUST123",
)

check(
    "Order ID extracted",
    extracted.order_id == "ORD456",
)

check(
    "Product extracted",
    extracted.product == "Python",
)

check(
    "Email extracted",
    extracted.customer.email
    == "rahul@example.com",
)

check(
    "Evidence extracted",
    len(extracted.evidence) > 0,
)

check(
    "Task 1 sentiment reused",
    extracted.sentiment in {
        "positive",
        "neutral",
        "negative",
    },
)


# -------------------------------------------------------------------
# Test 2: Missing information
# -------------------------------------------------------------------

incomplete_ticket = SupportTicket(
    ticket_id="T-0001",
    created_at=datetime(2026, 9, 14, 10, 0),
    customer=CustomerDetails(
        name="Rahul"
    ),
    order_id=None,
    product="Python",
    issue="My payment failed.",
    issue_category="payment",
    evidence=[],
    sentiment="negative",
    frustrated=True,
    urgent=False,
    sarcastic=False,
    risk_categories=[],
    customer_impact="individual",
)

missing = get_missing_information(
    incomplete_ticket
)

check(
    "Missing contact detected",
    "contact" in missing,
)

check(
    "Missing payment order detected",
    "order_id" in missing,
)

request = build_information_request(
    missing
)

check(
    "Missing information request generated",
    len(request) > 0,
)


# -------------------------------------------------------------------
# Test 3: Severity and priority
# -------------------------------------------------------------------

severity = derive_severity(
    risk_categories=["account_compromise"],
    urgent=False,
    frustrated=False,
    sentiment="neutral",
)

check(
    "High-risk issue gets critical severity",
    severity == "critical",
)

priority, score = calculate_priority(
    severity="critical",
    sentiment="negative",
    waiting_minutes=300,
    customer_impact="business",
    sla_consumed_ratio=0.80,
    urgent=True,
    frustrated=True,
)

check(
    "High-risk ticket receives critical priority",
    priority == "critical",
)

check(
    "Priority score calculated",
    score > 0,
)


# -------------------------------------------------------------------
# Test 4: SLA configuration
# -------------------------------------------------------------------

sla_config = SLAConfig(
    allowed_minutes={
        "critical": 60,
        "high": 120,
        "medium": 480,
        "low": 1440,
    },
    warning_threshold=0.75,
    business_start=time(9, 0),
    business_end=time(18, 0),
    business_days={0, 1, 2, 3, 4},
    holidays=set(),
)

# Monday 9:00 -> Monday 13:30 = 270 business minutes
start = datetime(
    2026, 9, 14, 9, 0
)

end = datetime(
    2026, 9, 14, 13, 30
)

minutes = business_minutes_between(
    start,
    end,
    sla_config,
)

check(
    "Business minutes calculated correctly",
    abs(minutes - 270) < 0.01,
)


# -------------------------------------------------------------------
# Test 5: Weekend excluded
# -------------------------------------------------------------------

friday = datetime(
    2026, 9, 11, 17, 0
)

monday = datetime(
    2026, 9, 14, 10, 0
)

weekend_minutes = business_minutes_between(
    friday,
    monday,
    sla_config,
)

# Friday 17-18 = 60
# Monday 9-10 = 60
# Weekend = excluded
check(
    "Weekend excluded from SLA",
    abs(weekend_minutes - 120) < 0.01,
)


# -------------------------------------------------------------------
# Test 6: Holiday excluded
# -------------------------------------------------------------------

add_holiday(
    sla_config,
    date(2026, 9, 15),
)

holiday_start = datetime(
    2026, 9, 14, 17, 0
)

holiday_end = datetime(
    2026, 9, 16, 10, 0
)

holiday_minutes = business_minutes_between(
    holiday_start,
    holiday_end,
    sla_config,
)

# Monday 17-18 = 60
# Tuesday holiday = 0
# Wednesday 9-10 = 60
check(
    "Configured holiday excluded",
    abs(holiday_minutes - 120) < 0.01,
)


# -------------------------------------------------------------------
# Test 7: 75% SLA warning
# -------------------------------------------------------------------

warning_config = SLAConfig(
    allowed_minutes={
        "high": 120,
    },
    warning_threshold=0.75,
    business_start=time(9, 0),
    business_end=time(18, 0),
    business_days={0, 1, 2, 3, 4},
)

warning_status = calculate_sla_status(
    created_at=datetime(
        2026, 9, 14, 9, 0
    ),
    current_time=datetime(
        2026, 9, 14, 10, 30
    ),
    priority="high",
    config=warning_config,
)

check(
    "75% SLA warning triggered",
    warning_status.warning is True,
)

check(
    "SLA not breached at 75%",
    warning_status.breached is False,
)


# -------------------------------------------------------------------
# Test 8: SLA breach
# -------------------------------------------------------------------

breach_status = calculate_sla_status(
    created_at=datetime(
        2026, 9, 14, 9, 0
    ),
    current_time=datetime(
        2026, 9, 14, 11, 1
    ),
    priority="high",
    config=warning_config,
)

check(
    "SLA breach detected",
    breach_status.breached is True,
)


# -------------------------------------------------------------------
# Test 9: Runtime SLA change
# -------------------------------------------------------------------

runtime_config = SLAConfig(
    allowed_minutes={
        "high": 120,
    },
    warning_threshold=0.75,
    business_start=time(9, 0),
    business_end=time(18, 0),
    business_days={0, 1, 2, 3, 4},
)

update_sla_rule(
    runtime_config,
    "high",
    240,
)

runtime_status = calculate_sla_status(
    created_at=datetime(
        2026, 9, 14, 9, 0
    ),
    current_time=datetime(
        2026, 9, 14, 11, 0
    ),
    priority="high",
    config=runtime_config,
)

check(
    "Runtime SLA rule change applied",
    runtime_status.allowed_minutes == 240,
)

check(
    "Runtime SLA change affects status",
    runtime_status.breached is False,
)


# -------------------------------------------------------------------
# Test 10: Agent routing
# -------------------------------------------------------------------

agents = [
    Agent(
        name="Unavailable Payments Agent",
        skills={"payments"},
        available=False,
        workload=1,
        max_workload=10,
    ),
    Agent(
        name="Available Payments Agent",
        skills={"payments"},
        available=True,
        workload=2,
        max_workload=10,
    ),
    Agent(
        name="Busy Payments Agent",
        skills={"payments"},
        available=True,
        workload=10,
        max_workload=10,
    ),
]

payment_ticket = SupportTicket(
    ticket_id="T-100",
    created_at=datetime(2026, 9, 14, 10, 0),
    customer=CustomerDetails(
        name="Rahul"
    ),
    order_id="ORD123",
    product="Python",
    issue="Payment failed.",
    issue_category="payment",
    evidence=["Receipt"],
    sentiment="negative",
    frustrated=True,
    urgent=False,
    sarcastic=False,
    risk_categories=[],
    customer_impact="individual",
)

routing = route_ticket(
    payment_ticket,
    agents,
    datetime(2026, 9, 14, 11, 0),
    runtime_config,
)

check(
    "Qualified available agent selected",
    routing.assigned_agent
    == "Available Payments Agent",
)


# -------------------------------------------------------------------
# Test 11: Unavailable team
# -------------------------------------------------------------------

unavailable_agents = [
    Agent(
        name="Payments Team",
        skills={"payments"},
        available=False,
        workload=1,
        max_workload=10,
    )
]

unavailable_routing = route_ticket(
    payment_ticket,
    unavailable_agents,
    datetime(2026, 9, 14, 11, 0),
    runtime_config,
)

check(
    "Unavailable team handled",
    unavailable_routing.assigned_queue
    == "unavailable_team",
)


# -------------------------------------------------------------------
# Test 12: After-hours normal request
# -------------------------------------------------------------------

after_hours = route_ticket(
    payment_ticket,
    agents,
    datetime(2026, 9, 14, 20, 0),
    runtime_config,
)

check(
    "After-hours normal request routed correctly",
    after_hours.assigned_queue
    == "next_working_day",
)

check(
    "After-hours request receives schedule",
    after_hours.scheduled_for is not None,
)


# -------------------------------------------------------------------
# Test 13: After-hours urgent request
# -------------------------------------------------------------------

on_call_agents = [
    Agent(
        name="On Call Security Agent",
        skills={"payments", "security"},
        available=True,
        workload=1,
        max_workload=10,
        on_call=True,
    )
]

payment_ticket.urgent = True
payment_ticket.priority = "critical"

after_hours_urgent = route_ticket(
    payment_ticket,
    on_call_agents,
    datetime(2026, 9, 14, 20, 0),
    runtime_config,
)

check(
    "Urgent after-hours request routed to on-call",
    after_hours_urgent.assigned_queue
    == "on_call",
)

check(
    "On-call agent selected",
    after_hours_urgent.assigned_agent
    == "On Call Security Agent",
)


# -------------------------------------------------------------------
# Test 14: Duplicate detection
# -------------------------------------------------------------------

existing_ticket = SupportTicket(
    ticket_id="T-OLD",
    created_at=datetime(
        2026, 9, 14, 9, 0
    ),
    customer=CustomerDetails(
        name="Rahul",
        email="rahul@example.com",
    ),
    order_id="ORD999",
    product="Python",
    issue="I was charged twice for my Python course.",
    issue_category="duplicate_payment",
    evidence=[],
    sentiment="negative",
    frustrated=True,
    urgent=False,
    sarcastic=False,
    risk_categories=["duplicate_payment"],
    customer_impact="individual",
)

new_ticket = SupportTicket(
    ticket_id="T-NEW",
    created_at=datetime(
        2026, 9, 14, 11, 0
    ),
    customer=CustomerDetails(
        name="Rahul",
        email="rahul@example.com",
    ),
    order_id="ORD999",
    product="Python",
    issue="I have been charged twice for my Python course.",
    issue_category="duplicate_payment",
    evidence=[],
    sentiment="negative",
    frustrated=True,
    urgent=False,
    sarcastic=False,
    risk_categories=["duplicate_payment"],
    customer_impact="individual",
)

duplicate = detect_duplicate(
    new_ticket,
    [existing_ticket],
    datetime(2026, 9, 14, 12, 0),
)

check(
    "Duplicate request detected",
    duplicate.is_duplicate is True,
)

check(
    "Correct duplicate ticket identified",
    duplicate.duplicate_ticket_id == "T-OLD",
)


# -------------------------------------------------------------------
# Test 15: Unrelated issues remain separate
# -------------------------------------------------------------------

security_ticket = SupportTicket(
    ticket_id="T-SEC",
    created_at=datetime(
        2026, 9, 14, 10, 0
    ),
    customer=CustomerDetails(
        email="rahul@example.com"
    ),
    order_id=None,
    product="Python",
    issue="Someone changed my account password.",
    issue_category="account_security",
    evidence=[],
    sentiment="negative",
    frustrated=False,
    urgent=True,
    sarcastic=False,
    risk_categories=["account_compromise"],
    customer_impact="individual",
)

payment_ticket_2 = SupportTicket(
    ticket_id="T-PAY",
    created_at=datetime(
        2026, 9, 14, 10, 0
    ),
    customer=CustomerDetails(
        email="rahul@example.com"
    ),
    order_id="ORD123",
    product="Python",
    issue="My payment failed.",
    issue_category="payment",
    evidence=[],
    sentiment="negative",
    frustrated=False,
    urgent=False,
    sarcastic=False,
    risk_categories=[],
    customer_impact="individual",
)

check(
    "Unrelated issues separated",
    issues_are_related(
        security_ticket,
        payment_ticket_2,
    ) is False,
)


# -------------------------------------------------------------------
# Test 16: Related issues grouped
# -------------------------------------------------------------------

payment_ticket_3 = SupportTicket(
    ticket_id="T-PAY2",
    created_at=datetime(
        2026, 9, 14, 10, 0
    ),
    customer=CustomerDetails(
        email="rahul@example.com"
    ),
    order_id="ORD123",
    product="Python",
    issue="The payment for my Python order failed.",
    issue_category="payment",
    evidence=[],
    sentiment="negative",
    frustrated=False,
    urgent=False,
    sarcastic=False,
    risk_categories=[],
    customer_impact="individual",
)

check(
    "Related payment issues grouped",
    issues_are_related(
        payment_ticket_2,
        payment_ticket_3,
    ) is True,
)

groups = group_related_issues(
    [
        security_ticket,
        payment_ticket_2,
        payment_ticket_3,
    ]
)

check(
    "Issue groups generated",
    len(groups) >= 2,
)


# -------------------------------------------------------------------
# Test 17: Masked handoff
# -------------------------------------------------------------------

handoff_ticket = SupportTicket(
    ticket_id="T-MASK",
    created_at=datetime(
        2026, 9, 14, 10, 0
    ),
    customer=CustomerDetails(
        name="Rahul Sharma",
        email="rahul@example.com",
        phone="+91 9876543210",
    ),
    order_id="ORD123",
    product="Python",
    issue=(
        "Please contact me at rahul@example.com "
        "or +91 9876543210."
    ),
    issue_category="payment",
    evidence=[],
    sentiment="negative",
    frustrated=True,
    urgent=False,
    sarcastic=False,
    risk_categories=[],
    customer_impact="individual",
)

handoff = generate_handoff_summary(
    handoff_ticket
)

check(
    "Handoff summary generated",
    len(handoff) > 0,
)

check(
    "Email masked",
    "rahul@example.com" not in handoff,
)

check(
    "Phone masked",
    "9876543210" not in handoff,
)

check(
    "Customer identity masked",
    "Rahul Sharma" not in handoff,
)


# -------------------------------------------------------------------
# Test 18: Complete workflow
# -------------------------------------------------------------------

workflow_messages = [
    ConversationMessage(
        text=(
            "My name is Priya Shah. "
            "My email is priya@example.com. "
            "Order ID ORD555. "
            "The product is Python. "
            "I was charged twice for my course. "
            "Screenshot attached."
        ),
        timestamp=datetime(
            2026, 9, 14, 10, 0
        ),
        role="user",
    )
]

workflow_agents = [
    Agent(
        name="Payment Specialist",
        skills={"payments"},
        available=True,
        workload=1,
        max_workload=10,
    )
]

workflow_result = process_unresolved_conversation(
    messages=workflow_messages,
    ticket_id="T-WORKFLOW",
    agents=workflow_agents,
    existing_tickets=[],
    current_time=datetime(
        2026, 9, 14, 11, 0
    ),
    sla_config=build_default_sla_config(),
    resolved=False,
)

check(
    "Complete workflow creates ticket",
    workflow_result.ticket is not None,
)

check(
    "Complete workflow extracts customer",
    workflow_result.ticket.customer.name
    == "Priya Shah",
)

check(
    "Complete workflow calculates priority",
    workflow_result.ticket.priority
    in {
        "critical",
        "high",
        "medium",
        "low",
    },
)

check(
    "Complete workflow calculates SLA",
    workflow_result.sla_status is not None,
)

check(
    "Complete workflow routes ticket",
    workflow_result.routing is not None,
)

check(
    "Complete workflow generates handoff",
    workflow_result.ticket.handoff_summary
    is not None,
)


# -------------------------------------------------------------------
# Test 19: Resolved conversation
# -------------------------------------------------------------------

resolved_result = process_unresolved_conversation(
    messages=workflow_messages,
    ticket_id="T-RESOLVED",
    agents=workflow_agents,
    existing_tickets=[],
    current_time=datetime(
        2026, 9, 14, 11, 0
    ),
    sla_config=build_default_sla_config(),
    resolved=True,
)

check(
    "Resolved conversation does not create active ticket",
    resolved_result.ticket is None,
)


# -------------------------------------------------------------------
# Final result
# -------------------------------------------------------------------

print()
print("=" * 60)
print("TASK 2 TEST SUMMARY")
print("=" * 60)
print(f"Passed: {passed}")
print(f"Failed: {failed}")

if failed == 0:
    print()
    print("TASK 2 STATUS: COMPLETE")
else:
    print()
    print("TASK 2 STATUS: NOT COMPLETE")
    print("Fix the failed tests before moving to Task 3.")

raise SystemExit(
    0 if failed == 0 else 1
)