"""
Information extraction for Task 2.

This module extracts:

- Customer name
- Customer ID
- Order ID
- Product
- Issue
- Issue category
- Evidence
- Contact details
- Customer impact

Task 1 sentiment and risk analysis are reused here.
"""

import re
from typing import List, Optional

from task1.analyzer import analyze_message
from task1.models import ConversationMessage

from .models import CustomerDetails, ExtractedTicketData


# -------------------------------------------------------------------
# Regular expressions
# -------------------------------------------------------------------

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"
)

CUSTOMER_ID_PATTERN = re.compile(
    r"\b(?:CUSTOMER\s*ID|CUSTOMER_ID|CUSTOMERID|CUST(?:OMER)?)"
    r"[\s:_-]*([A-Z0-9]{2,20})\b",
    re.IGNORECASE,
)

ORDER_ID_PATTERN = re.compile(
    r"\b(?:ORDER\s*ID|ORDER_ID|ORDERID|ORDER|ORD)"
    r"[\s:_-]*([A-Z0-9]{2,20})\b",
    re.IGNORECASE,
)


# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------

def _conversation_text(
    messages: List[ConversationMessage],
) -> str:
    """
    Combine all conversation messages into one searchable string.
    """
    if not messages:
        return ""

    return " ".join(
        str(message.text)
        for message in messages
        if getattr(message, "text", None)
    )


def _clean(value: Optional[str]) -> Optional[str]:
    """
    Clean extracted text.
    """
    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    return value


# -------------------------------------------------------------------
# Customer name
# -------------------------------------------------------------------

def extract_customer_name(text: str) -> Optional[str]:
    """
    Extract customer name from phrases such as:

    My name is Rahul Sharma.
    I am Rahul Sharma.
    This is Rahul Sharma.
    """

    patterns = [
        r"\bmy\s+name\s+is\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,3})",
        r"\bname\s*:\s*([A-Za-z]+(?:\s+[A-Za-z]+){0,3})",
        r"\bi\s+am\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,3})",
        r"\bthis\s+is\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,3})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            name = match.group(1).strip()

            # Remove common trailing words accidentally captured.
            name = re.split(
                r"\b(?:customer|order|product|email|phone|my)\b",
                name,
                flags=re.IGNORECASE,
            )[0].strip()

            if name:
                return name

    return None


# -------------------------------------------------------------------
# Customer ID
# -------------------------------------------------------------------

def extract_customer_id(text: str) -> Optional[str]:
    """
    Extract Customer ID from common customer-service formats.

    Supported examples:
        Customer ID CUST123
        Customer ID: CUST123
        Customer_ID: CUST123
        CustomerID CUST123
        CUST123
        CUST-123
    """

    if not text:
        return None

    patterns = [
        # Customer ID: CUST123
        r"\bcustomer\s*id\s*[:=\-_]?\s*([A-Z0-9][A-Z0-9\-_]{1,20})\b",

        # Customer_ID: CUST123
        r"\bcustomer_id\s*[:=\-_]?\s*([A-Z0-9][A-Z0-9\-_]{1,20})\b",

        # CustomerID: CUST123
        r"\bcustomerid\s*[:=\-_]?\s*([A-Z0-9][A-Z0-9\-_]{1,20})\b",

        # Cust ID: CUST123
        r"\bcust\s*id\s*[:=\-_]?\s*([A-Z0-9][A-Z0-9\-_]{1,20})\b",

        # Cust123 / Customer123
        r"\b(cust(?:omer)?[-_]?[A-Z0-9]{2,20})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            customer_id = match.group(1).strip()

            # Normalize:
            # cust-123 -> CUST123
            # cust_123 -> CUST123
            customer_id = re.sub(r"[-_\s]", "", customer_id)

            return customer_id.upper()

    return None


# -------------------------------------------------------------------
# Order ID
# -------------------------------------------------------------------

def extract_order_id(text: str) -> Optional[str]:
    """
    Extract order ID from conversation text.

    Supported examples:
        Order ID ORD456
        Order ID: ORD456
        My order ID is ORD456
        ORDER123
        ORD456
    """

    # ---------------------------------------------------------------
    # 1. Explicit "Order ID" statements
    # ---------------------------------------------------------------

    patterns = [
        r"\border\s*id\s*(?:is|=|:|-)?\s*(ORD[-_ ]?[A-Z0-9]{2,20})\b",
        r"\borderid\s*(?:is|=|:|-)?\s*(ORD[-_ ]?[A-Z0-9]{2,20})\b",
        r"\border\s*(?:number|no\.?|#)\s*(?:is|=|:|-)?\s*(ORD[-_ ]?[A-Z0-9]{2,20})\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            order_id = match.group(1)

            # Normalize ORD-456 / ORD_456 / ORD 456 -> ORD456
            order_id = re.sub(
                r"[-_ ]",
                "",
                order_id,
            )

            return order_id.upper()

    # ---------------------------------------------------------------
    # 2. Direct ORD123 format anywhere in the text
    # ---------------------------------------------------------------

    match = re.search(
        r"\bORD[-_ ]?[A-Z0-9]{2,20}\b",
        text,
        re.IGNORECASE,
    )

    if match:
        order_id = match.group(0)

        order_id = re.sub(
            r"[-_ ]",
            "",
            order_id,
        )

        return order_id.upper()

    return None 


# -------------------------------------------------------------------
# Product
# -------------------------------------------------------------------

def extract_product(text: str) -> Optional[str]:
    """
    Extract product information from the conversation.

    Examples:
        The product is Python.
        Product: Python
        My product is Python.
        Product Python
    """

    # ---------------------------------------------------------------
    # 1. Explicit product statements
    # ---------------------------------------------------------------

    patterns = [
        r"\bthe\s+product\s+is\s+([A-Za-z0-9][A-Za-z0-9 .&_-]*?)(?=\s*(?:\.|!|\?|,|;|$))",

        r"\bmy\s+product\s+is\s+([A-Za-z0-9][A-Za-z0-9 .&_-]*?)(?=\s*(?:\.|!|\?|,|;|$))",

        r"\bproduct\s*:\s*([A-Za-z0-9][A-Za-z0-9 .&_-]*?)(?=\s*(?:\.|!|\?|,|;|$))",

        r"\bproduct\s+is\s+([A-Za-z0-9][A-Za-z0-9 .&_-]*?)(?=\s*(?:\.|!|\?|,|;|$))",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            product = match.group(1).strip()

            if product:
                return product

    # ---------------------------------------------------------------
    # 2. Common product names
    # ---------------------------------------------------------------

    known_products = [
    "Wireless Headphones",
    "Bluetooth Headphones",
    "Noise Cancelling Headphones",
    "Wireless Mouse",
    "Gaming Mouse",
    "Wireless Keyboard",
    "Power BI",
    "Data Science",
    "Machine Learning",
    "Artificial Intelligence",
    "Python",
    "Laptop",
    "Mobile",
    "Phone",
    "Tablet",
    "Headphones",
    "Earphones",
    "Keyboard",
    "Mouse",
    "Monitor",
    "Subscription",
    "Membership",
]

    for product in known_products:
        if re.search(
            rf"\b{re.escape(product)}\b",
            text,
            re.IGNORECASE,
        ):
            return product

    return None

# -------------------------------------------------------------------
# Issue
# -------------------------------------------------------------------

def extract_issue(text: str) -> Optional[str]:
    """
    Extract the customer's issue.
    """

    patterns = [
        r"\bissue\s*:\s*(.+?)(?:[.!?]|$)",
        r"\bproblem\s*:\s*(.+?)(?:[.!?]|$)",
        r"\bcomplaint\s*:\s*(.+?)(?:[.!?]|$)",
        r"\bmy\s+issue\s+is\s+(.+?)(?:[.!?]|$)",
        r"\bmy\s+problem\s+is\s+(.+?)(?:[.!?]|$)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            issue = match.group(1).strip()

            if issue:
                return issue

    # Detect important issue phrases.
    issue_phrases = [
        "charged twice",
        "payment failed",
        "payment failure",
        "account compromised",
        "account hacked",
        "password changed",
        "cannot login",
        "can't login",
        "login failed",
        "refund not received",
        "order not received",
        "product damaged",
        "wrong product",
        "duplicate payment",
        "charged extra",
    ]

    for phrase in issue_phrases:
        match = re.search(
            rf".{{0,80}}\b{re.escape(phrase)}\b.{{0,120}}",
            text,
            re.IGNORECASE,
        )

        if match:
            return match.group(0).strip()

    return text.strip() if text.strip() else None


# -------------------------------------------------------------------
# Issue category
# -------------------------------------------------------------------

def extract_issue_category(text: str) -> str:
    """
    Classify the issue into a simple Task 2 category.
    """

    lowered = text.lower()

    # Specific high-risk categories must be checked before broad terms.
    if any(phrase in lowered for phrase in (
        "charged twice", "charged two times", "duplicate payment",
        "paid twice", "double charged", "billed twice",
    )):
        return "duplicate_payment"

    if any(phrase in lowered for phrase in (
        "legal action", "sue your company", "take you to court",
        "contact my lawyer", "lawyer", "legal notice",
    )):
        return "legal_threat"

    if any(phrase in lowered for phrase in (
        "password", "hacked", "compromised", "account security",
        "someone changed my account", "unauthorized access",
        "without my permission", "stolen account",
    )):
        return "account_security"

    if (
        "payment" in lowered
        or "charged" in lowered
        or "transaction" in lowered
        or "refund" in lowered
    ):
        return "payment"

    if (
        "login" in lowered
        or "log in" in lowered
        or "sign in" in lowered
    ):
        return "login"

    if (
        "order" in lowered
        or "delivery" in lowered
        or "delivered" in lowered
    ):
        return "order"

    if (
        "damaged" in lowered
        or "broken" in lowered
        or "defective" in lowered
    ):
        return "product"

    return "general"


# -------------------------------------------------------------------
# Evidence
# -------------------------------------------------------------------

def extract_evidence(text: str) -> List[str]:
    """
    Extract evidence or attachments mentioned in the conversation.

        Examples:
        Screenshot attached.
        Invoice uploaded.
        Customer uploaded a product video.
        Evidence: Customer uploaded a product video.
    """

    evidence = []

    evidence_patterns = [
        r"\bscreenshot(?:\s+(?:attached|uploaded))?\b",
        r"\binvoice(?:\s+(?:attached|uploaded))?\b",
        r"\breceipt(?:\s+(?:attached|uploaded))?\b",
        r"\bphoto(?:\s+(?:attached|uploaded))?\b",
        r"\bimage(?:\s+(?:attached|uploaded))?\b",
        r"\bpdf(?:\s+(?:attached|uploaded))?\b",
        r"\bdocument(?:\s+(?:attached|uploaded))?\b",
        r"\bproof(?:\s+(?:attached|uploaded))?\b",
        r"\bvideo(?:\s+(?:attached|uploaded))?\b",
    ]

    for pattern in evidence_patterns:
        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE,
        )

        for item in matches:
            item = item.strip()

            if item and item.lower() not in {
                existing.lower() for existing in evidence
            }:
                evidence.append(item)

    # Explicit Evidence: ... statement
    evidence_match = re.search(
        r"\bevidence\s*[:=-]\s*(.+?)(?:[.!?]|$)",
        text,
        re.IGNORECASE,
    )

    if evidence_match:
        evidence_description = evidence_match.group(1).strip()

        if evidence_description:
            evidence.append(evidence_description)

    # Transaction/order/invoice/error references
    if re.search(
        r"\b(?:invoice|receipt|transaction|txn|error\s*code)\b",
        text,
        re.IGNORECASE,
    ):
        if not any(
            item.lower() == "reference"
            for item in evidence
        ):
            evidence.append("reference")

    return evidence


# -------------------------------------------------------------------
# Contact information
# -------------------------------------------------------------------

def extract_contact_details(text: str) -> dict:
    """
    Extract email and phone.
    """

    email_match = EMAIL_PATTERN.search(text)

    phone_match = PHONE_PATTERN.search(text)

    return {
        "email": (
            email_match.group(0)
            if email_match
            else None
        ),
        "phone": (
            phone_match.group(0)
            if phone_match
            else None
        ),
    }


# -------------------------------------------------------------------
# Customer impact
# -------------------------------------------------------------------

def extract_customer_impact(text: str) -> str:
    """
    Determine customer impact.
    """

    lowered = text.lower()

    business_words = [
        "business",
        "company",
        "customers",
        "multiple users",
        "many users",
        "organization",
    ]

    widespread_words = [
        "everyone",
        "all users",
        "system wide",
        "system-wide",
        "multiple customers",
    ]

    if any(word in lowered for word in widespread_words):
        return "widespread"

    if any(word in lowered for word in business_words):
        return "business"

    return "individual"


# -------------------------------------------------------------------
# Task 1 analysis
# -------------------------------------------------------------------

def analyze_customer_message(
    messages: List[ConversationMessage],
):
    """
    Reuse Task 1 analysis for sentiment/risk information.
    """

    if not messages:
        return None

    try:
        result = analyze_message(messages)

        return result

    except Exception:
        # Keep Task 2 extraction usable even if Task 1
        # implementation changes.
        return None


# -------------------------------------------------------------------
# Build CustomerDetails
# -------------------------------------------------------------------

def build_customer_details(
    text: str,
) -> CustomerDetails:
    """
    Build CustomerDetails from conversation text.
    """

    contact = extract_contact_details(text)

    return CustomerDetails(
        name=extract_customer_name(text),
        customer_id=extract_customer_id(text),
        email=contact["email"],
        phone=contact["phone"],
    )


# -------------------------------------------------------------------
# Safe Task 1 value extraction
# -------------------------------------------------------------------

def _get_analysis_value(
    analysis,
    field_name: str,
    default=None,
):
    """
    Safely read a field from Task 1 analysis.

    Supports dataclass/object/dict results.
    """

    if analysis is None:
        return default

    if isinstance(analysis, dict):
        return analysis.get(
            field_name,
            default,
        )

    return getattr(
        analysis,
        field_name,
        default,
    )


# -------------------------------------------------------------------
# Main extraction function
# -------------------------------------------------------------------

def extract_ticket_data(
    messages: List[ConversationMessage],
) -> ExtractedTicketData:
    """
    Extract structured Task 2 information from conversation.
    """

    text = _conversation_text(messages)

    customer = build_customer_details(text)

    order_id = extract_order_id(text)

    product = extract_product(text)

    issue = extract_issue(text)

    issue_category = extract_issue_category(text)

    evidence = extract_evidence(text)

    customer_impact = extract_customer_impact(text)

    # Reuse Task 1.
    analysis = analyze_customer_message(messages)

    sentiment = _get_analysis_value(
        analysis,
        "sentiment",
        "neutral",
    )

    frustrated = _get_analysis_value(
        analysis,
        "frustrated",
        False,
    )

    urgent = _get_analysis_value(
        analysis,
        "urgent",
        False,
    )

    sarcastic = _get_analysis_value(
        analysis,
        "sarcastic",
        False,
    )

    risk_categories = _get_analysis_value(
        analysis,
        "risk_categories",
        [],
    )

    # Normalize values.
    if sentiment is None:
        sentiment = "neutral"

    if not isinstance(sentiment, str):
        sentiment = str(sentiment)

    if not isinstance(frustrated, bool):
        frustrated = bool(frustrated)

    if not isinstance(urgent, bool):
        urgent = bool(urgent)

    if not isinstance(sarcastic, bool):
        sarcastic = bool(sarcastic)

    if risk_categories is None:
        risk_categories = []

    if not isinstance(risk_categories, list):
        try:
            risk_categories = list(risk_categories)
        except Exception:
            risk_categories = [str(risk_categories)]

    return ExtractedTicketData(
        customer=customer,
        order_id=order_id,
        product=product,
        issue=issue,
        issue_category=issue_category,
        evidence=evidence,
        sentiment=sentiment,
        frustrated=frustrated,
        urgent=urgent,
        sarcastic=sarcastic,
        risk_categories=risk_categories,
        customer_impact=customer_impact,
    )


# -------------------------------------------------------------------
# Compatibility aliases
# -------------------------------------------------------------------

extract_information = extract_ticket_data
extract_ticket = extract_ticket_data
extract_data = extract_ticket_data
extract = extract_ticket_data


# -------------------------------------------------------------------
# Missing information helper
# -------------------------------------------------------------------

def get_missing_fields(
    data: ExtractedTicketData,
) -> List[str]:
    """
    Return important missing fields.

    This helper is intentionally separate from
    task2.missing_info.py.
    """

    missing = []

    if data.customer is None:
        missing.append("customer")

    else:
        if not data.customer.name:
            missing.append("name")

        if not data.customer.email and not data.customer.phone:
            missing.append("contact")

    if not data.order_id:
        missing.append("order_id")

    if not data.product:
        missing.append("product")

    if not data.issue:
        missing.append("issue")

    if not data.evidence:
        missing.append("evidence")

    return missing


# -------------------------------------------------------------------
# Manual test
# -------------------------------------------------------------------

if __name__ == "__main__":

    test_messages = [
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
            timestamp=None,
            role="user",
        )
    ]

    result = extract_ticket_data(
        test_messages
    )

    print("Customer:", result.customer)
    print("Order ID:", result.order_id)
    print("Product:", result.product)
    print("Issue:", result.issue)
    print("Category:", result.issue_category)
    print("Evidence:", result.evidence)
    print("Sentiment:", result.sentiment)
    print("Frustrated:", result.frustrated)
    print("Urgent:", result.urgent)
    print("Sarcastic:", result.sarcastic)
    print("Risk:", result.risk_categories)
    print("Impact:", result.customer_impact)