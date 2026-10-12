"""
Information extraction for Task 2.

Extracts customer, order, product, issue, evidence, contact details,
customer impact, and Task 1 sentiment/risk information.
"""

import re
from typing import List, Optional

from task1.analyzer import analyze_message
from task1.models import ConversationMessage
from .models import CustomerDetails, ExtractedTicketData


EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"
)

# Require an actual identifier after a label. A bare word "order" is not an ID.
ORDER_ID_VALUE = r"(?:ORD[-_ ]?[A-Z0-9]{2,20}|ORDER[-_ ]?[A-Z0-9]{2,20})"
CUSTOMER_ID_VALUE = r"(?:CUST(?:OMER)?[-_ ]?[A-Z0-9]{2,20})"


def _conversation_text(messages: List[ConversationMessage]) -> str:
    """Combine conversation messages into searchable text."""
    if not messages:
        return ""
    return " ".join(
        str(message.text)
        for message in messages
        if getattr(message, "text", None)
    )


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


def extract_customer_name(text: str) -> Optional[str]:
    """Extract an explicitly stated customer name."""
    if not text:
        return None

    patterns = [
        r"\bmy\s+name\s+is\s+([A-Za-z]+(?:[ '-][A-Za-z]+){0,3})",
        r"\bcustomer\s+name\s*[:=]\s*([A-Za-z]+(?:[ '-][A-Za-z]+){0,3})",
        r"\bname\s*:\s*([A-Za-z]+(?:[ '-][A-Za-z]+){0,3})",
        r"\bi\s+am\s+([A-Za-z]+(?:[ '-][A-Za-z]+){0,3})",
        r"\bthis\s+is\s+([A-Za-z]+(?:[ '-][A-Za-z]+){0,3})",
    ]
    stop_words = {
        "customer", "order", "product", "email", "phone", "my",
        "and", "but", "i", "the", "please", "contact", "issue",
    }

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        words = match.group(1).strip().split()
        while words and words[-1].lower() in stop_words:
            words.pop()
        name = " ".join(words).strip(" -'")
        if name and all(re.fullmatch(r"[A-Za-z'-]+", word) for word in words):
            return name
    return None


def extract_customer_id(text: str) -> Optional[str]:
    """Extract customer IDs from labelled fields or explicit CUST123 formats."""
    if not text:
        return None

    patterns = [
        rf"\bcustomer\s*[_ ]?id\s*[:=#-]?\s*({CUSTOMER_ID_VALUE})\b",
        rf"\bcust\s*[_ ]?id\s*[:=#-]?\s*({CUSTOMER_ID_VALUE})\b",
        r"\b(CUST(?:OMER)?[-_]?[A-Z0-9]{2,20})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = re.sub(r"[-_ ]", "", match.group(1)).upper()
            # Do not accept labels without a meaningful identifier suffix.
            if re.fullmatch(r"CUSTOMER[A-Z0-9]{2,20}|CUST[A-Z0-9]{2,20}", value):
                return value
    return None


def extract_order_id(text: str) -> Optional[str]:
    """
    Extract order IDs only when an identifier contains a valid prefix and
    at least two identifier characters, e.g. ORD5678 or ORDER-5678.
    Never treat the standalone word 'order' as an order ID.
    """
    if not text:
        return None

    patterns = [
        rf"\border\s*[_ ]?id\s*(?:is|=|:|#|-)?\s*({ORDER_ID_VALUE})\b",
        rf"\borderid\s*(?:is|=|:|#|-)?\s*({ORDER_ID_VALUE})\b",
        rf"\border\s*(?:number|no\.?|#)\s*(?:is|=|:|-)?\s*({ORDER_ID_VALUE})\b",
        rf"\b({ORDER_ID_VALUE})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = re.sub(r"[-_ ]", "", match.group(1)).upper()
            if re.fullmatch(r"(?:ORD|ORDER)[A-Z0-9]{2,20}", value):
                return value
    return None


def extract_product(text: str) -> Optional[str]:
    """Extract an explicitly labelled product or a recognized product name."""
    if not text:
        return None

    patterns = [
        r"\b(?:the\s+)?product\s*(?:is|:)\s*([A-Za-z0-9][A-Za-z0-9 .&_-]*?)(?=\s*(?:[.!?,;]|$|\b(?:issue|problem|order\s+id|customer\s+id|contact|email|phone|evidence)\b))",
        r"\bmy\s+product\s+is\s+([A-Za-z0-9][A-Za-z0-9 .&_-]*?)(?=\s*(?:[.!?,;]|$))",
    ]
    stop_terms = re.compile(
        r"\b(?:issue|problem|order|customer|contact|email|phone|evidence|stopped|not|won't|will not|doesn't|does not|isn't|is not|has|have|after|because)\b",
        re.IGNORECASE,
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            product = stop_terms.split(match.group(1))[0].strip(" .,:;_-")
            if product:
                return product

    known_products = [
        "Noise Cancelling Headphones", "Wireless Headphones",
        "Bluetooth Headphones", "Wireless Keyboard", "Wireless Mouse",
        "Gaming Mouse", "Power BI", "Data Science", "Machine Learning",
        "Artificial Intelligence", "Headphones", "Earphones", "Laptop",
        "Mobile Phone", "Mobile", "Tablet", "Keyboard", "Mouse",
        "Monitor", "Subscription", "Membership", "Python",
    ]
    for product in sorted(known_products, key=len, reverse=True):
        if re.search(rf"\b{re.escape(product)}\b", text, re.IGNORECASE):
            return product
    return None


def extract_issue(text: str) -> Optional[str]:
    """Extract a labelled issue or a useful issue phrase."""
    if not text:
        return None

    patterns = [
        r"\bissue\s*:\s*(.+?)(?:[.!?]|$)",
        r"\bproblem\s*:\s*(.+?)(?:[.!?]|$)",
        r"\bcomplaint\s*:\s*(.+?)(?:[.!?]|$)",
        r"\bmy\s+issue\s+is\s+(.+?)(?:[.!?]|$)",
        r"\bmy\s+problem\s+is\s+(.+?)(?:[.!?]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1).strip():
            return match.group(1).strip()

    issue_phrases = [
        "headphones stopped working", "headphones are not charging",
        "headphones won't charge", "stopped charging", "not charging",
        "charged twice", "duplicate payment", "payment failed",
        "payment failure", "account compromised", "account hacked",
        "password changed", "cannot log in", "can't login", "login failed",
        "refund not received", "refund has not arrived",
        "order not received", "order has not arrived",
        "product damaged", "wrong product", "charged extra",
    ]
    for phrase in issue_phrases:
        match = re.search(rf".{{0,80}}\b{re.escape(phrase)}\b.{{0,120}}", text, re.IGNORECASE)
        if match:
            return match.group(0).strip(" .,:;")
    return text.strip() or None


def extract_issue_category(text: str) -> str:
    """Classify issue using specific/high-risk categories before broad categories."""
    lowered = (text or "").lower()

    if any(p in lowered for p in (
        "charged twice", "charged two times", "duplicate payment",
        "paid twice", "double charged", "billed twice",
    )):
        return "duplicate_payment"

    if any(p in lowered for p in (
        "legal action", "sue your company", "take you to court",
        "contact my lawyer", "lawyer", "legal notice",
    )):
        return "legal_threat"

    if any(p in lowered for p in (
        "password", "hacked", "compromised", "account security",
        "someone changed my account", "unauthorized access",
        "without my permission", "stolen account",
    )):
        return "account_security"

    if any(p in lowered for p in (
        "refund", "payment", "charged", "transaction", "billing",
    )):
        return "payment"

    if any(p in lowered for p in (
        "headphones", "earphones", "laptop", "keyboard", "mouse",
        "monitor", "product damaged", "broken", "defective",
        "stopped working", "not charging", "won't charge",
        "will not charge", "doesn't work", "does not work",
    )):
        return "product"

    if any(p in lowered for p in ("login", "log in", "sign in")):
        return "login"

    if any(p in lowered for p in ("order", "delivery", "delivered", "shipment")):
        return "order"

    return "general"


def extract_evidence(text: str) -> List[str]:
    """Extract evidence/attachment mentions and explicitly supplied evidence."""
    if not text:
        return []

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
        r"\berror\s*code\b",
    ]
    for pattern in evidence_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            item = match.group(0).strip()
            if item.lower() not in {x.lower() for x in evidence}:
                evidence.append(item)

    explicit = re.search(r"\bevidence\s*[:=-]\s*(.+?)(?:[.!?]|$)", text, re.IGNORECASE)
    if explicit:
        description = explicit.group(1).strip()
        if description and description.lower() not in {x.lower() for x in evidence}:
            evidence.append(description)

    if re.search(r"\b(?:invoice|receipt|transaction|txn|error\s*code)\b", text, re.IGNORECASE):
        if "reference" not in {x.lower() for x in evidence}:
            evidence.append("reference")
    return evidence


def extract_contact_details(text: str) -> dict:
    """Extract email and phone details."""
    email_match = EMAIL_PATTERN.search(text or "")
    phone_match = PHONE_PATTERN.search(text or "")
    return {
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0) if phone_match else None,
    }


def extract_customer_impact(text: str) -> str:
    """Estimate impact scope from explicit wording."""
    lowered = (text or "").lower()
    if any(w in lowered for w in (
        "everyone", "all users", "system wide", "system-wide",
        "multiple customers", "multiple users", "many users",
    )):
        return "widespread"
    if any(w in lowered for w in ("business", "company", "organization")):
        return "business"
    return "individual"


def analyze_customer_message(messages: List[ConversationMessage]):
    """Reuse Task 1 analysis for sentiment/risk information."""
    if not messages:
        return None
    try:
        return analyze_message(messages)
    except Exception:
        return None


def build_customer_details(text: str) -> CustomerDetails:
    """Build CustomerDetails from conversation text."""
    contact = extract_contact_details(text)
    return CustomerDetails(
        name=extract_customer_name(text),
        customer_id=extract_customer_id(text),
        email=contact["email"],
        phone=contact["phone"],
    )


def _get_analysis_value(analysis, field_name: str, default=None):
    """Read a field from Task 1 analysis whether it is a dict or object."""
    if analysis is None:
        return default
    if isinstance(analysis, dict):
        return analysis.get(field_name, default)
    return getattr(analysis, field_name, default)


def extract_ticket_data(messages: List[ConversationMessage]) -> ExtractedTicketData:
    """Extract structured Task 2 information from conversation messages."""
    text = _conversation_text(messages)
    customer = build_customer_details(text)
    order_id = extract_order_id(text)
    product = extract_product(text)
    issue = extract_issue(text)
    issue_category = extract_issue_category(text)
    evidence = extract_evidence(text)
    customer_impact = extract_customer_impact(text)

    analysis = analyze_customer_message(messages)
    sentiment = _get_analysis_value(analysis, "sentiment", "neutral")
    frustrated = _get_analysis_value(analysis, "frustrated", False)
    urgent = _get_analysis_value(analysis, "urgent", False)
    sarcastic = _get_analysis_value(analysis, "sarcastic", False)
    risk_categories = _get_analysis_value(analysis, "risk_categories", [])

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


# Compatibility aliases
extract_information = extract_ticket_data
extract_ticket = extract_ticket_data
extract_data = extract_ticket_data
extract = extract_ticket_data


def get_missing_fields(data: ExtractedTicketData) -> List[str]:
    """
    Return fields that need clarification.

    Contact is satisfied by either email or phone. Order ID, product, and
    evidence may be required by the downstream policy; retain the existing
    project's required-field behavior here.
    """
    missing = []
    customer = getattr(data, "customer", None)

    if customer is None:
        missing.append("customer")
    else:
        if not getattr(customer, "name", None) and not getattr(customer, "customer_id", None):
            missing.append("customer")
        if not getattr(customer, "email", None) and not getattr(customer, "phone", None):
            missing.append("contact")

    if not getattr(data, "order_id", None):
        missing.append("order_id")
    if not getattr(data, "product", None):
        missing.append("product")
    if not getattr(data, "issue", None):
        missing.append("issue")
    if not getattr(data, "evidence", None):
        missing.append("evidence")

    return missing


if __name__ == "__main__":
    test_messages = [
        ConversationMessage(
            text=(
                "My name is Rahul Sharma. Customer ID CUST123. "
                "My order ID is ORD456. The product is Python. "
                "I paid twice and I am very frustrated. "
                "My email is rahul@example.com. Screenshot attached."
            ),
            timestamp=None,
            role="user",
        )
    ]
    result = extract_ticket_data(test_messages)
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
