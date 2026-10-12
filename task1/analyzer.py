"""
Task 1 - Multilingual Sentiment and Risk Analyzer

Covers:
- Positive
- Neutral
- Negative
- Frustrated
- Urgent
- Sarcastic
- English / Hindi / Marathi / Spanish / French
- Confidence scores
- High-risk detection
- Calm high-risk complaints
- Account compromise
- Duplicate payment
- Legal threats

Rule-based implementation designed for deterministic testing.
"""

import re
from typing import Dict, List, Optional

from .models import MessageAnalysis


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
# POSITIVE VOCABULARY
# ============================================================

POSITIVE_WORDS = {
    "en": [
        "good",
        "great",
        "excellent",
        "amazing",
        "happy",
        "helpful",
        "thank",
        "thanks",
        "thank you",
        "perfect",
        "love",
        "satisfied",
        "resolved",
        "solve",
        "solved",
        "working",
        "wonderful",
    ],

    "hi": [
        "accha",
        "achha",
        "bahut accha",
        "khush",
        "dhanyavad",
        "shukriya",
        "santusht",
        "धन्यवाद",
        "शुक्रिया",
        "अच्छा",
        "अच्छी",
        "खुश",
    ],

    "mr": [
        "छान",
        "चांगले",
        "मस्त",
        "धन्यवाद",
        "आनंदी",
        "समाधानी",
        "धन्यवाद",
        "छान आहे",
    ],

    "es": [
        "bueno",
        "buena",
        "excelente",
        "genial",
        "feliz",
        "gracias",
        "perfecto",
        "satisfecho",
        "resuelto",
    ],

    "fr": [
        "bon",
        "bonne",
        "excellent",
        "génial",
        "heureux",
        "merci",
        "parfait",
        "satisfait",
        "résolu",
    ],
}


# ============================================================
# NEGATIVE VOCABULARY
# ============================================================

NEGATIVE_WORDS = {
    "en": [
        "bad",
        "terrible",
        "poor",
        "wrong",
        "problem",
        "issue",
        "failed",
        "failure",
        "broken",
        "cannot",
        "can't",
        "unable",
        "nobody has solved",
        "disappointed",
        "unhappy",
        "worst",
        "refund",
        "complaint",
        "not working",
        "doesn't work",
        "didn't work",
        "not arrived",
        "has not arrived",
        "hasn't arrived",
        "not received",
        "has not received",
        "still waiting",
        "waiting",
        "delay",
        "delayed",
        "late",
    ],

    "hi": [
        "bura",
        "galat",
        "problem",
        "pareshan",
        "pareshani",
        "nahi",
        "nahin",
        "kharaab",
        "shikayat",
        "समस्या",
        "परेशान",
        "परेशानी",
        "गलत",
        "नहीं",
        "शिकायत",
    ],

    "mr": [
        "वाईट",
        "चुकीचे",
        "समस्या",
        "त्रास",
        "तक्रार",
        "काम करत नाही",
        "नाही",
        "उशीर",
        "आले नाही",
    ],

    "es": [
        "malo",
        "mala",
        "problema",
        "error",
        "fallo",
        "queja",
        "decepcionado",
        "no funciona",
        "no ha llegado",
        "esperando",
        "retraso",
    ],

    "fr": [
        "mauvais",
        "problème",
        "erreur",
        "échec",
        "plainte",
        "déçu",
        "ne fonctionne pas",
        "pas arrivé",
        "attends",
        "retard",
    ],
}


# ============================================================
# FRUSTRATION
# ============================================================

FRUSTRATION_PATTERNS = [
    "this is frustrating",
    "so frustrating",
    "very frustrating",
    "extremely frustrating",
    "i am frustrated",
    "i'm frustrated",
    "fed up",
    "sick of this",
    "tired of this",
    "how many times",
    "again and again",
    "still not working",
    "still doesn't work",
    "nothing is working",
    "this is ridiculous",
    "ridiculous",
    "waste of time",
    "pareshan",
    "bahut pareshan",
    "muy frustrado",
    "très frustré",

    # Hindi
    "बहुत परेशान",
    "परेशान हूं",
    "परेशान हूँ",

    # Marathi
    "खूप त्रास",
    "खूप त्रास झाला",
    "त्रास झाला",
]


# ============================================================
# URGENCY
# ============================================================

URGENCY_PATTERNS = [
    "urgent",
    "urgently",
    "emergency",
    "asap",
    "immediately",
    "right now",
    "critical",
    "cannot wait",
    "need help now",
    "help me now",
    "please help immediately",

    # Hindi transliteration
    "jaldi",
    "bahut zaruri",
    "turant",
    "mujhe turant madad chahiye",

    # Hindi
    "तुरंत",
    "जल्दी",
    "बहुत जरूरी",
    "मुझे तुरंत मदद चाहिए",
    "मुझे जल्दी मदद चाहिए",
    "तुरंत मदद",
    "जल्दी मदद",

    # Marathi transliteration
    "mala lagech madat havi",
    "lagech madat",
    "tatkal madat",

    # Marathi
    "मला लगेच मदत हवी",
    "लगेच मदत",
    "तात्काळ मदत",

    # Spanish
    "urgente",
    "urgentemente",
    "inmediatamente",
    "necesito ayuda ahora",

    # French
    "urgent",
    "urgentement",
    "immédiatement",
    "j'ai besoin d'aide maintenant",
]


# ============================================================
# SARCASM
# ============================================================

SARCASM_PATTERNS = [
    "great job",
    "excellent job",
    "thanks for nothing",
    "what a surprise",
    "yeah right",
    "amazing service",
    "amazing support",
    "wow, amazing support",
    "wow amazing support",
    "best service ever",
    "best support ever",
    "so perfect",
    "love waiting",
    "oh fantastic",
    "just what i needed",
    "what a great service",
    "thanks a lot for nothing",
    "another great",
    "great, another",
    "fantastic, another",
    "brilliant, another",
    "great, just great",

    # Common sarcastic customer-service expressions
    "wow, great support",
    "wow great support",
    "thanks for the great support",
    "thanks for nothing",


    # Important:
    # "perfect" alone can be genuine positive.
    # Therefore it is NOT included here by itself.
]


# ============================================================
# HIGH-RISK PATTERNS
# ============================================================

RISK_PATTERNS = {

    "account_compromise": [
        "account compromised",
        "account compromise",
        "my account is compromised",
        "my account was compromised",
        "account has been compromised",
        "my account has been compromised",
        "account hacked",
        "account has been hacked",
        "my account was hacked",
        "my account is hacked",
        "someone hacked my account",
        "someone accessed my account",
        "someone has accessed my account",
        "someone used my account",
        "someone is using my account",
        "unauthorized transaction",
        "unauthorised transaction",
        "unauthorized payment",
        "unauthorised payment",
        "unauthorized access",
        "unauthorised access",
        "unrecognized transaction",
        "unrecognised transaction",
        "unrecognized payment",
        "unrecognised payment",
        "unknown transaction",
        "unknown payment",
        "fraudulent transaction",
        "fraudulent payment",
        "fraud transaction",
        "fraud payment",
        "transaction i did not make",
        "transaction i didn't make",
        "payment i did not make",
        "payment i didn't make",
        "not my transaction",
        "not my payment",
        "i did not make this transaction",
        "i didn't make this transaction",
        "i did not make this payment",
        "i didn't make this payment",
        "unauthorized login",
        "unauthorised login",
        "unknown login",
        "unknown access",
    ],

    "duplicate_payment": [
        "charged twice",
        "charged two times",
        "charged multiple times",
        "charged more than once",
        "duplicate payment",
        "duplicate charge",
        "double payment",
        "double charged",
        "payment duplicated",
        "paid twice",
        "payment taken twice",
        "money deducted twice",
        "amount deducted twice",
        "same payment twice",
        "same amount charged twice",
    ],

    "legal_threat": [
        "legal action",
        "take legal action",
        "will take legal action",
        "lawyer",
        "attorney",
        "court",
        "sue",
        "sue you",
        "legal complaint",
        "consumer court",
        "consumer forum",
        "file a case",
        "file a lawsuit",
        "police complaint",
    ],
}


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize(text: str) -> str:

    text = text.lower().strip()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


# ============================================================
# LANGUAGE DETECTION
# ============================================================

def detect_language(text: str) -> str:

    normalized = _normalize(text)

    # --------------------------------------------------------
    # Devanagari
    # --------------------------------------------------------

    if re.search(
        r"[\u0900-\u097F]",
        text,
    ):

        # Marathi-specific indicators
        marathi_words = [
            "मला",
            "माझे",
            "माझा",
            "माझी",
            "आहे",
            "हवी",
            "हवे",
            "कृपया",
            "तक्रार",
            "पैसे",
            "लगेच",
            "मदत",
        ]

        if any(
            word in text
            for word in marathi_words
        ):
            return "mr"

        return "hi"

    # --------------------------------------------------------
    # Hindi transliteration
    # --------------------------------------------------------

    hindi_words = [
        "mujhe",
        "mera",
        "meri",
        "mere",
        "hai",
        "nahi",
        "nahin",
        "kripya",
        "madad",
        "dhanyavad",
        "shukriya",
        "pareshan",
        "paisa",
        "khata",
        "turant",
        "jaldi",
    ]

    if any(
        re.search(
            r"\b" + re.escape(word) + r"\b",
            normalized,
        )
        for word in hindi_words
    ):
        return "hi"

    # --------------------------------------------------------
    # Marathi transliteration
    # --------------------------------------------------------

    marathi_words_translit = [
        "mala",
        "majha",
        "majhe",
        "majhi",
        "ahe",
        "havi",
        "hawa",
        "lagech",
        "madat",
    ]

    if any(
        re.search(
            r"\b" + re.escape(word) + r"\b",
            normalized,
        )
        for word in marathi_words_translit
    ):
        return "mr"

    # --------------------------------------------------------
    # Spanish
    # --------------------------------------------------------

    spanish_words = [
        "hola",
        "gracias",
        "problema",
        "ayuda",
        "cuenta",
        "pago",
        "transacción",
        "transaccion",
        "urgente",
        "por favor",
        "no funciona",
    ]

    if any(
        word in normalized
        for word in spanish_words
    ):
        return "es"

    # --------------------------------------------------------
    # French
    # --------------------------------------------------------

    french_words = [
        "bonjour",
        "merci",
        "problème",
        "probleme",
        "aide",
        "compte",
        "paiement",
        "transaction",
        "s'il vous plaît",
        "ne fonctionne pas",
        "j'ai besoin d'aide",
        "mon compte",
        "mon paiement",

    ]

    if any(
        word in normalized
        for word in french_words
    ):
        return "fr"

    return "en"


# ============================================================
# MATCHING
# ============================================================

def _contains_pattern(
    text: str,
    patterns: List[str],
) -> bool:
    """Match whole words/phrases instead of arbitrary substrings."""
    normalized = _normalize(text)

    for pattern in patterns:
        phrase = _normalize(pattern)
        if not phrase:
            continue

        # Phrase boundaries prevent matches such as "great" inside
        # unrelated words, while still allowing punctuation around phrases.
        if re.search(
            r"(?<!\w)" + re.escape(phrase) + r"(?!\w)",
            normalized,
            flags=re.IGNORECASE,
        ):
            return True

    return False


def _count_vocabulary_matches(
    text: str,
    words: List[str],
    *,
    ignore_negated: bool = False,
) -> int:
    """Count matched vocabulary terms and optionally ignore negated positives."""
    normalized = _normalize(text)
    count = 0

    for word in words:
        phrase = _normalize(word)
        if not phrase:
            continue

        match = re.search(
            r"(?<!\w)" + re.escape(phrase) + r"(?!\w)",
            normalized,
            flags=re.IGNORECASE,
        )
        if not match:
            continue

        if ignore_negated:
            prefix = normalized[max(0, match.start() - 24):match.start()]
            if re.search(
                r"(?:\bnot\s+|\bno\s+|\bnever\s+|\bn't\s+|\bisn't\s+|\baren't\s+|\bwasn't\s+|\bweren't\s+)$",
                prefix,
            ):
                continue

        count += 1

    return count


# ============================================================
# RISK DETECTION
# ============================================================

def detect_risk_categories(
    text: str,
) -> List[str]:

    normalized = _normalize(text)

    detected = []

    for category, patterns in RISK_PATTERNS.items():

        if _contains_pattern(
            normalized,
            patterns,
        ):
            detected.append(category)

    return detected


# ============================================================
# SENTIMENT
# ============================================================

def detect_sentiment(
    text: str,
    language: str,
    sarcastic: bool = False,
) -> str:
    """
    Deterministic sentiment classification.

    Strong complaint/frustration signals take precedence over incidental
    positive words such as "solved", "great", or "wonderful". A message is
    positive only when it expresses genuine satisfaction/resolution without
    a conflicting complaint or unresolved-service signal.
    """
    normalized = _normalize(text)
    positive_words = POSITIVE_WORDS.get(language, [])
    negative_words = NEGATIVE_WORDS.get(language, [])

    positive_count = _count_vocabulary_matches(
        normalized, positive_words, ignore_negated=True
    )
    negative_count = _count_vocabulary_matches(normalized, negative_words)

    frustration_patterns = FRUSTRATION_PATTERNS + [
        "nobody has solved my problem",
        "nobody solved my problem",
        "no one has solved my problem",
        "no one solved my problem",
        "nobody has helped",
        "no one has helped",
        "contacted support three times",
        "contacted support multiple times",
        "contacted support several times",
        "three times",
        "again and again",
        "still unresolved",
        "not been resolved",
        "has not been resolved",
        "nothing has been fixed",
        "this service is ridiculous",
        "nobody has solved my problem",
        "nobody cares",
        "no one cares",
        "extremely disappointed",
        "very disappointed",
        "not happy",
        "unacceptable",
        "ridiculous",
    ]
    strong_negative_patterns = [
        "nobody has solved my problem",
        "nobody solved my problem",
        "no one has solved my problem",
        "no one solved my problem",
        "nobody has helped",
        "no one has helped",
        "this is ridiculous",
        "service is ridiculous",
        "extremely disappointed",
        "very disappointed",
        "unacceptable",
        "fed up",
        "waste of time",
        "nothing has been fixed",
        "still unresolved",
        "not been resolved",
        "has not been resolved",
        "not happy",
    ]
    service_failure_patterns = [
        "not working", "doesn't work", "didn't work", "not arrived",
        "has not arrived", "hasn't arrived", "not received",
        "has not received", "still waiting", "failed", "failure",
        "unable", "cannot", "can't", "nobody solved", "nobody has solved",
        "no one solved", "no one has solved", "not resolved",
        "not fixed", "not solved",
    ]

    has_frustration = _contains_pattern(normalized, frustration_patterns)
    has_strong_negative = _contains_pattern(normalized, strong_negative_patterns)
    has_service_failure = _contains_pattern(normalized, service_failure_patterns)

    # Negated praise is not positive sentiment.
    if re.search(
        r"\b(?:not|never|no longer)\b.{0,25}\b(?:good|great|happy|satisfied|wonderful|perfect)\b",
        normalized,
    ):
        positive_count = 0

    # Strong complaints win over incidental positive vocabulary.
    if sarcastic or has_strong_negative or has_frustration or has_service_failure:
        return "negative"

    # Positive resolution language is positive only when the complaint has
    # genuinely been resolved and the message is not otherwise negative.
    positive_resolution_patterns = [
        "thank you", "thanks", "solved my problem", "problem solved",
        "issue resolved", "resolved my issue", "you solved",
        "thanks for solving", "everything works", "works perfectly",
    ]
    has_positive_resolution = _contains_pattern(
        normalized, positive_resolution_patterns
    )

    if has_positive_resolution and negative_count == 0 and not sarcastic:
        return "positive"

    if negative_count > positive_count:
        return "negative"
    if positive_count > negative_count:
        return "positive"
    return "neutral"


# ============================================================
# CONFIDENCE
# ============================================================

def _confidence_scores(
    sentiment: str,
    frustrated: bool,
    urgent: bool,
    sarcastic: bool,
    risk_categories: List[str],
) -> Dict[str, float]:

    sentiment_confidence = {
        "positive": 0.90,
        "negative": 0.90,
        "neutral": 0.75,
    }.get(
        sentiment,
        0.75,
    )

    return {
        "sentiment": sentiment_confidence,

        "frustrated": (
            0.90
            if frustrated
            else 0.75
        ),

        "urgent": (
            0.95
            if urgent
            else 0.75
        ),

        "sarcastic": (
            0.90
            if sarcastic
            else 0.75
        ),
    }


# ============================================================
# RESPONSE TONE
# ============================================================

def _recommended_tone(
    sentiment: str,
    frustrated: bool,
    urgent: bool,
    sarcastic: bool,
    risk_categories: List[str],
) -> str:

    if risk_categories:
        return "calm_professional"

    if urgent:
        return "urgent_professional"

    if sarcastic:
        return "calm_professional"

    if frustrated or sentiment == "negative":
        return "empathetic"

    if sentiment == "positive":
        return "friendly"

    return "professional"


# ============================================================
# MAIN ANALYZER
# ============================================================

def analyze_message(
    text: str,
    history: Optional[List[str]] = None,
) -> MessageAnalysis:

    if not isinstance(text, str):
        text = str(text)

    text = text.strip()

    language = detect_language(text)

    normalized = _normalize(text)

    risk_categories = detect_risk_categories(
        text
    )

    frustration_indicators = FRUSTRATION_PATTERNS + [
        "contacted support three times",
        "contacted support multiple times",
        "contacted support several times",
        "nobody has solved my problem",
        "nobody solved my problem",
        "no one has solved my problem",
        "no one solved my problem",
        "nobody has helped",
        "no one has helped",
        "extremely disappointed",
        "very disappointed",
        "unacceptable",
        "not happy",
        "this service is ridiculous",
        "Nobody has solved my problem",
        "still unresolved",
    ]
    frustrated = _contains_pattern(normalized, frustration_indicators)

    explicit_urgent = _contains_pattern(
        normalized,
        URGENCY_PATTERNS,
    )

    sarcastic = _contains_pattern(
        normalized,
        SARCASM_PATTERNS,
    )

    # Conversation context can make an otherwise ambiguous positive phrase
    # sarcastic (for example, "Great, thanks" after repeated payment failures).
    if not sarcastic and history:
        recent_context = " ".join(
            str(item) for item in history[-5:]
        ).lower()
        context_has_unresolved_issue = _contains_pattern(
            recent_context,
            NEGATIVE_WORDS.get(language, []) + FRUSTRATION_PATTERNS
            + ["payment failed", "charged twice", "not working", "still waiting"],
        )
        context_sensitive_phrase = _contains_pattern(
            normalized,
            [
                "great", "wonderful", "fantastic", "sure",
                "thanks", "thank you", "brilliant",
            ],
        )
        if context_has_unresolved_issue and context_sensitive_phrase:
            sarcastic = True

    sentiment = detect_sentiment(
        text,
        language,
        sarcastic=sarcastic,
    )

    # Repeated unresolved negative messages in recent history should be
    # treated as frustration. The caller can use this signal for escalation.
    if history:
        recent_context = " ".join(str(item) for item in history[-5:])
        repeated_complaint = _contains_pattern(
            recent_context,
            FRUSTRATION_PATTERNS + [
                "still waiting", "not resolved", "not fixed",
                "nobody helped", "contacted support three times",
                "contacted support multiple times",
            ],
        )
        if repeated_complaint:
            frustrated = True
            if sentiment == "positive":
                sentiment = "negative"

    # High-risk issues are urgent even when the wording is calm/neutral.
    urgent = explicit_urgent or bool(risk_categories)

    confidence = _confidence_scores(
        sentiment=sentiment,
        frustrated=frustrated,
        urgent=urgent,
        sarcastic=sarcastic,
        risk_categories=risk_categories,
    )

    tone = _recommended_tone(
        sentiment=sentiment,
        frustrated=frustrated,
        urgent=urgent,
        sarcastic=sarcastic,
        risk_categories=risk_categories,
    )

    return MessageAnalysis(
        language=language,
        sentiment=sentiment,
        frustrated=frustrated,
        urgent=urgent,
        sarcastic=sarcastic,
        confidence=confidence,
        risk_categories=risk_categories,
        recommended_tone=tone,
    )


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    examples = [
        "Thank you so much, you solved my problem!",
        "Great job, another payment failed.",
        "मुझे तुरंत मदद चाहिए",
        "मला लगेच मदत हवी",
        "Hello, I noticed an unauthorized transaction on my account.",
        "I was charged twice for the same order.",
        "I'll take legal action if this isn't resolved.",
    ]

    for message in examples:

        print("\n" + "=" * 70)
        print("MESSAGE:", message)
        print("=" * 70)

        result = analyze_message(message)

        print("Language:", result.language)
        print("Sentiment:", result.sentiment)
        print("Frustrated:", result.frustrated)
        print("Urgent:", result.urgent)
        print("Sarcastic:", result.sarcastic)
        print("Tone:", result.recommended_tone)
        print("Confidence:", result.confidence)
        print("Risk:", result.risk_categories)
