import sys
from pathlib import Path
from datetime import datetime, timedelta


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORTS
# ============================================================

from task1.analyzer import analyze_message
from task1.conversation import ConversationManager
from task1.time_utils import (
    is_business_hours,
    next_working_day,
)


# ============================================================
# TEST COUNTERS
# ============================================================

TOTAL_TESTS = 0
PASSED_TESTS = 0
FAILED_TESTS = 0


# ============================================================
# TEST HELPER
# ============================================================

def check(
    condition: bool,
    description: str,
):

    global TOTAL_TESTS
    global PASSED_TESTS
    global FAILED_TESTS

    TOTAL_TESTS += 1

    if condition:

        PASSED_TESTS += 1

        print(
            f"  PASS: {description}"
        )

    else:

        FAILED_TESTS += 1

        print(
            f"  FAIL: {description}"
        )


# ============================================================
# 1. POSITIVE
# ============================================================

def test_positive():

    print("\n[1] POSITIVE MESSAGE")

    result = analyze_message(
        "Thank you so much, you solved my problem!"
    )

    print(result)

    check(
        result.sentiment == "positive",
        "Positive sentiment detected",
    )

    check(
        result.frustrated is False,
        "Not frustrated",
    )

    check(
        result.urgent is False,
        "Not urgent",
    )


# ============================================================
# 2. NEUTRAL
# ============================================================

def test_neutral():

    print("\n[2] NEUTRAL MESSAGE")

    result = analyze_message(
        "Can you tell me the price of the Power BI course?"
    )

    print(result)

    check(
        result.sentiment == "neutral",
        "Neutral sentiment detected",
    )

    check(
        result.frustrated is False,
        "Not frustrated",
    )


# ============================================================
# 3. NEGATIVE
# ============================================================

def test_negative():

    print("\n[3] NEGATIVE MESSAGE")

    result = analyze_message(
        "I am disappointed with the service."
    )

    print(result)

    check(
        result.sentiment == "negative",
        "Negative sentiment detected",
    )


# ============================================================
# 4. FRUSTRATED
# ============================================================

def test_frustrated():

    print("\n[4] FRUSTRATED MESSAGE")

    result = analyze_message(
        "This is ridiculous, nobody is helping me!"
    )

    print(result)

    check(
        result.sentiment == "negative",
        "Negative sentiment detected",
    )

    check(
        result.frustrated is True,
        "Frustration detected",
    )


# ============================================================
# 5. URGENT
# ============================================================

def test_urgent():

    print("\n[5] URGENT MESSAGE")

    result = analyze_message(
        "This is urgent! I need help immediately."
    )

    print(result)

    check(
        result.urgent is True,
        "Urgency detected",
    )


# ============================================================
# 6. SARCASM
# ============================================================

def test_sarcasm():

    print("\n[6] SARCASM")

    result = analyze_message(
        "Great job, another payment failed."
    )

    print(result)

    check(
        result.sarcastic is True,
        "Sarcasm detected",
    )

    check(
        result.sentiment == "negative",
        "Sarcastic complaint classified as negative",
    )


# ============================================================
# 7. ACCOUNT COMPROMISE
# ============================================================

def test_account_compromise():

    print("\n[7] ACCOUNT COMPROMISE")

    result = analyze_message(
        "I see an unauthorized login on my account."
    )

    print(result)

    check(
        "account_compromise"
        in result.risk_categories,
        "Account compromise detected",
    )

    check(
        result.urgent is True,
        "High-risk account issue marked urgent",
    )


# ============================================================
# 8. DUPLICATE PAYMENT
# ============================================================

def test_duplicate_payment():

    print("\n[8] DUPLICATE PAYMENT")

    result = analyze_message(
        "I was charged twice for the same payment."
    )

    print(result)

    check(
        "duplicate_payment"
        in result.risk_categories,
        "Duplicate payment detected",
    )

    check(
        result.urgent is True,
        "Duplicate payment marked urgent",
    )


# ============================================================
# 9. LEGAL THREAT
# ============================================================

def test_legal_threat():

    print("\n[9] LEGAL THREAT")

    result = analyze_message(
        "I'll take legal action if this isn't resolved."
    )

    print(result)

    check(
        "legal_threat"
        in result.risk_categories,
        "Legal threat detected",
    )

    check(
        result.urgent is True,
        "Legal threat marked urgent",
    )


# ============================================================
# 10. HINDI
# ============================================================

def test_hindi():

    print("\n[10] HINDI")

    result = analyze_message(
        "मुझे तुरंत मदद चाहिए"
    )

    print(result)

    check(
        result.language == "hi",
        "Hindi detected",
    )

    check(
        result.urgent is True,
        "Hindi urgent message detected",
    )


# ============================================================
# 11. MARATHI
# ============================================================

def test_marathi():

    print("\n[11] MARATHI")

    result = analyze_message(
        "मला लगेच मदत हवी"
    )

    print(result)

    check(
        result.language == "mr",
        "Marathi detected",
    )

    check(
        result.urgent is True,
        "Marathi urgent message detected",
    )


# ============================================================
# 12. SPANISH
# ============================================================

def test_spanish():

    print("\n[12] SPANISH")

    result = analyze_message(
        "Gracias por la ayuda"
    )

    print(result)

    check(
        result.language == "es",
        "Spanish detected",
    )

    check(
        result.sentiment == "positive",
        "Spanish positive sentiment detected",
    )


# ============================================================
# 13. FRENCH
# ============================================================

def test_french():

    print("\n[13] FRENCH")

    result = analyze_message(
        "Merci pour votre aide"
    )

    print(result)

    check(
        result.language == "fr",
        "French detected",
    )

    check(
        result.sentiment == "positive",
        "French positive sentiment detected",
    )


# ============================================================
# 14. CONFIDENCE SCORES
# ============================================================

def test_confidence_scores():

    print("\n[14] CONFIDENCE SCORES")

    result = analyze_message(
        "This is a serious problem and I need help immediately."
    )

    print(result.confidence)

    required_fields = [
        "sentiment",
        "frustrated",
        "urgent",
        "sarcastic",
    ]

    for field in required_fields:

        check(
            field in result.confidence,
            f"Confidence exists for {field}",
        )

        if field in result.confidence:

            value = result.confidence[field]

            check(
                0.0 <= value <= 1.0,
                f"{field} confidence is between 0 and 1",
            )


# ============================================================
# 15. RESPONSE TONE
# ============================================================

def test_response_tone():

    print("\n[15] RESPONSE TONE")

    manager = ConversationManager()

    current_time = datetime(
        2026,
        9,
        15,
        11,
        0,
    )

    manager.add_message(
        "This is ridiculous, nobody is helping me!",
        current_time,
        role="user",
    )

    instruction = (
        manager.get_current_tone_instruction()
    )

    response = manager.adjust_response(
        "Your request is being reviewed."
    )

    print("Tone instruction:")
    print(instruction)

    print("\nAdjusted response:")
    print(response)

    check(
        "empathetic" in instruction.lower()
        or "calm" in instruction.lower(),
        "Frustrated customer receives calming/empathetic tone",
    )

    check(
        "Your request is being reviewed."
        in response,
        "Original business response remains unchanged",
    )


# ============================================================
# 16. CALM HIGH-RISK ESCALATION
# ============================================================

def test_calm_high_risk_escalation():

    print("\n[16] CALM HIGH-RISK ESCALATION")

    manager = ConversationManager()

    current_time = datetime(
        2026,
        9,
        15,
        11,
        0,
    )

    manager.add_message(
        "I see an unauthorized login on my account.",
        current_time,
    )

    result = manager.check_escalation(
        current_time
    )

    print(result)

    check(
        result.required is True,
        "Calm high-risk complaint escalates",
    )

    check(
        result.queue == "priority_support",
        "Business-hours high-risk issue goes to priority support",
    )

    check(
        "high_risk:account_compromise"
        in result.activated_conditions,
        "Account compromise condition recorded",
    )

    check(
        result.conversation_summary is not None,
        "Conversation summary recorded",
    )

    check(
        result.reason is not None,
        "Escalation reason recorded",
    )


# ============================================================
# 17. AFTER-HOURS URGENT
# ============================================================

def test_after_hours_urgent():

    print("\n[17] AFTER-HOURS URGENT")

    manager = ConversationManager()

    current_time = datetime(
        2026,
        9,
        15,
        22,
        0,
    )

    manager.add_message(
        "My account has been hacked! I need help immediately.",
        current_time,
    )

    result = manager.check_escalation(
        current_time
    )

    print(result)

    check(
        result.required is True,
        "After-hours urgent complaint escalates",
    )

    check(
        result.queue == "on_call",
        "Urgent after-hours issue goes to on-call",
    )

    check(
        "after_hours_urgent"
        in result.activated_conditions,
        "After-hours urgent condition recorded",
    )


# ============================================================
# 18. AFTER-HOURS NORMAL COMPLAINT
# ============================================================

def test_after_hours_normal_complaint():

    print("\n[18] AFTER-HOURS NORMAL COMPLAINT")

    manager = ConversationManager()

    current_time = datetime(
        2026,
        9,
        15,
        22,
        0,
    )

    manager.add_message(
        "My course certificate has not arrived. Please check it.",
        current_time,
    )

    result = manager.check_escalation(
        current_time
    )

    print(result)

    check(
        result.required is True,
        "Normal after-hours complaint is scheduled",
    )

    check(
        result.queue == "next_working_day",
        "Normal complaint goes to next working day",
    )

    check(
        result.scheduled_for is not None,
        "Next working day is recorded",
    )

    check(
        "after_hours_normal_complaint"
        in result.activated_conditions,
        "Normal after-hours condition recorded",
    )


# ============================================================
# 19. EXACTLY 15 MINUTES
# ============================================================

def test_exactly_15_minutes():

    print("\n[19] EXACTLY 15 MINUTES")

    manager = ConversationManager()

    start_time = datetime(
        2026,
        9,
        15,
        10,
        0,
    )

    current_time = (
        start_time
        + timedelta(minutes=15)
    )

    manager.add_message(
        "My payment failed and I am disappointed.",
        start_time,
    )

    result = manager.check_escalation(
        current_time
    )

    print(result)

    check(
        "negative_unresolved_15_minutes"
        not in result.activated_conditions,
        "Exactly 15 minutes does not trigger >15 minute rule",
    )


# ============================================================
# 20. MORE THAN 15 MINUTES
# ============================================================

def test_more_than_15_minutes():

    print("\n[20] MORE THAN 15 MINUTES")

    manager = ConversationManager()

    start_time = datetime(
        2026,
        9,
        15,
        10,
        0,
    )

    current_time = (
        start_time
        + timedelta(minutes=16)
    )

    manager.add_message(
        "My payment failed and I am disappointed.",
        start_time,
    )

    manager.add_message(
        "Please wait while we investigate.",
        start_time
        + timedelta(minutes=2),
        role="assistant",
    )

    result = manager.check_escalation(
        current_time
    )

    print(result)

    check(
        result.required is True,
        "Negative unresolved conversation escalates after 15 minutes",
    )

    check(
        "negative_unresolved_15_minutes"
        in result.activated_conditions,
        "15-minute condition recorded",
    )


# ============================================================
# 21. REPEATED NEGATIVE
# ============================================================

def test_repeated_negative():

    print("\n[21] REPEATED NEGATIVE MESSAGES")

    manager = ConversationManager()

    base_time = datetime(
        2026,
        9,
        15,
        10,
        0,
    )

    messages = [

        "My payment is not working.",

        "I am still waiting and nobody is helping me.",

        "This is ridiculous, my problem is still not fixed.",
    ]

    for index, message in enumerate(messages):

        manager.add_message(
            message,
            base_time
            + timedelta(minutes=index * 2),
        )

    result = manager.check_escalation(
        base_time
        + timedelta(minutes=6)
    )

    print(result)

    check(
        result.required is True,
        "Repeated negative messages escalate",
    )

    check(
        "repeated_negative_messages"
        in result.activated_conditions,
        "Repeated-negative condition recorded",
    )


# ============================================================
# 22. CONVERSATION HISTORY
# ============================================================

def test_conversation_history():

    print("\n[22] CONVERSATION HISTORY")

    manager = ConversationManager()

    base_time = datetime(
        2026,
        9,
        15,
        10,
        0,
    )

    manager.add_message(
        "My payment failed.",
        base_time,
    )

    manager.add_message(
        "Please wait while we check.",
        base_time + timedelta(minutes=1),
        role="assistant",
    )

    manager.add_message(
        "I am still waiting. Nobody is helping me.",
        base_time + timedelta(minutes=3),
    )

    history = manager.get_history()

    print(
        f"History messages: {len(history)}"
    )

    check(
        len(history) == 3,
        "Conversation history is retained",
    )

    result = manager.check_escalation(
        base_time + timedelta(minutes=3)
    )

    print(result)

    check(
        result.conversation_summary is not None,
        "Escalation includes conversation summary",
    )

    check(
        "My payment failed."
        in result.conversation_summary,
        "Conversation summary contains earlier message",
    )


# ============================================================
# 23. RESOLVED CONVERSATION
# ============================================================

def test_resolved_conversation():

    print("\n[23] RESOLVED CONVERSATION")

    manager = ConversationManager()

    start_time = datetime(
        2026,
        9,
        15,
        10,
        0,
    )

    manager.add_message(
        "My payment failed and I am disappointed.",
        start_time,
    )

    manager.mark_resolved()

    result = manager.check_escalation(
        start_time + timedelta(minutes=30)
    )

    print(result)

    check(
        "negative_unresolved_15_minutes"
        not in result.activated_conditions,
        "Resolved conversation does not trigger unresolved 15-minute escalation",
    )


# ============================================================
# 24. SIMULATED TIME
# ============================================================

def test_simulated_time():

    print("\n[24] SIMULATED TIME")

    morning = datetime(
        2026,
        9,
        15,
        10,
        0,
    )

    night = datetime(
        2026,
        9,
        15,
        22,
        0,
    )

    check(
        is_business_hours(morning) is True,
        "10:00 is business hours",
    )

    check(
        is_business_hours(night) is False,
        "22:00 is outside business hours",
    )

    next_day = next_working_day(
        night
    )

    print(
        f"Simulated next working day: {next_day}"
    )

    check(
        next_day.hour == 9,
        "Next working day starts at 09:00",
    )


# ============================================================
# FINAL REPORT
# ============================================================

def print_final_report():

    print("\n")
    print("=" * 80)
    print("TASK 1 FINAL VALIDATION REPORT")
    print("=" * 80)

    print(
        f"Total checks : {TOTAL_TESTS}"
    )

    print(
        f"Passed       : {PASSED_TESTS}"
    )

    print(
        f"Failed       : {FAILED_TESTS}"
    )

    if TOTAL_TESTS > 0:

        percentage = (
            PASSED_TESTS
            / TOTAL_TESTS
            * 100
        )

        print(
            f"Pass rate    : {percentage:.2f}%"
        )

    print("-" * 80)

    if FAILED_TESTS == 0:

        print(
            "TASK 1 STATUS: COMPLETE"
        )

        print(
            "All implemented Task 1 requirements passed."
        )

    else:

        print(
            "TASK 1 STATUS: NOT COMPLETE"
        )

        print(
            "Fix the failed checks before moving to Task 2."
        )

    print("=" * 80)


# ============================================================
# MAIN
# ============================================================

def main():

    test_positive()
    test_neutral()
    test_negative()
    test_frustrated()
    test_urgent()
    test_sarcasm()

    test_account_compromise()
    test_duplicate_payment()
    test_legal_threat()

    test_hindi()
    test_marathi()
    test_spanish()
    test_french()

    test_confidence_scores()
    test_response_tone()

    test_calm_high_risk_escalation()
    test_after_hours_urgent()
    test_after_hours_normal_complaint()

    test_exactly_15_minutes()
    test_more_than_15_minutes()

    test_repeated_negative()
    test_conversation_history()
    test_resolved_conversation()

    test_simulated_time()

    print_final_report()


if __name__ == "__main__":
    main()