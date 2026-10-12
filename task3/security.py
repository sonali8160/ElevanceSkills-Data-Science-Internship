"""Access control, prompt-injection screening and PII masking for Task 3."""
import re

ALLOWED_ROLES = {
    "admin": {"update", "rollback", "view", "scan", "stage", "activate", "monitor", "configure"},
    "developer": {"update", "view", "scan", "stage", "monitor"},
    "update_operator": {"update", "view", "scan", "stage", "activate", "monitor"},
    "viewer": {"view"},
}

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|system|developer)\s+instructions?",
    r"ignore\s+all\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above|system|developer)\s+instructions?",
    r"(reveal|print|show|expose)\s+(the\s+)?(system\s+)?prompt",
    r"developer\s+(message|instructions?)",
    r"system\s+prompt",
    r"jailbreak",
    r"act\s+as\s+(an?\s+)?(unrestricted|unfiltered|different)\s+",
]

def check_access(role, action):
    """Return True only when the role explicitly allows the action."""
    return action in ALLOWED_ROLES.get(str(role or "").lower(), set())

def detect_prompt_injection(text):
    """Detect common direct prompt-injection instructions in document text."""
    normalized = re.sub(r"[\u200b-\u200f\ufeff]", "", str(text or ""))
    normalized = re.sub(r"\s+", " ", normalized).lower()
    return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in INJECTION_PATTERNS)

def mask_sensitive_data(text):
    """Mask common email, phone, payment-card and customer identifiers."""
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL]", str(text or ""))
    text = re.sub(r"(?<!\d)(?:\+?\d{1,3}[ .-]?)?(?:\(?\d{3}\)?[ .-]?)?\d{3}[ .-]?\d{4}(?!\d)", "[PHONE]", text)
    text = re.sub(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)", "[CARD]", text)
    text = re.sub(r"\b(?:SSN|Aadhaar|Aadhar|Customer ID|CustomerID)\s*[:#-]?\s*[A-Z0-9-]{6,16}\b", "[IDENTIFIER]", text, flags=re.IGNORECASE)
    return text
