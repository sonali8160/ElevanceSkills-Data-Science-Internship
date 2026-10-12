# task6/multilingual_chat.py

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
import unicodedata


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class Task6Config:
    # English + 3 additional languages
    languages: List[str] = field(
        default_factory=lambda: [
            "english",
            "hindi",
            "marathi",
            "spanish"
        ]
    )

    language_threshold: float = 0.50
    intent_threshold: float = 0.50

    context_messages: int = 10
    inactivity_minutes: int = 30
    restore_hours: int = 24


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class Message:
    text: str
    language: str
    intent: str
    timestamp: datetime
    confidence: float


@dataclass
class Session:
    session_id: str
    customer_id: str
    messages: List[Message] = field(default_factory=list)
    summary: str = ""
    active: bool = True
    last_activity: Optional[datetime] = None
    ended_at: Optional[datetime] = None


# ============================================================
# CHATBOT
# ============================================================

class MultilingualChatbot:

    def __init__(self, config=None):

        self.config = config or Task6Config()

        # Active sessions
        self.sessions: Dict[str, Session] = {}

        # Expired/closed sessions
        self.closed_sessions: Dict[str, Session] = {}

        # ----------------------------------------------------
        # LANGUAGE WORDS
        # ----------------------------------------------------

        self.language_words = {

            "english": {
                "where", "is", "my", "the", "order",
                "product", "refund", "payment", "delivery",
                "help", "please", "want", "need", "status",
                "problem", "and", "also", "was", "delayed",
                "what", "when", "why", "how"
            },

            "hindi": {
                "mera", "meri", "mere", "mujhe",
                "kab", "kahan", "kaha", "hai",
                "hain", "chahiye", "nahi",
                "paise", "madad", "kyun",
                "kaise", "aur", "yeh", "yah",
                "order"
            },

            "marathi": {
                "माझा", "माझी", "माझे", "मला",
                "कधी", "कुठे", "आहे", "आहेत",
                "पाहिजे", "नाही", "पैसे",
                "मदत", "का", "कसे", "आणि",
                "ऑर्डर"
            },

            "spanish": {
                "hola", "donde", "dónde", "esta",
                "está", "mi", "pedido", "producto",
                "reembolso", "pago", "ayuda",
                "quiero", "necesito", "cuando",
                "cuándo", "problema", "y"
            }
        }

        # ----------------------------------------------------
        # INTENT WORDS
        # ----------------------------------------------------

        self.intent_words = {

            "order_status": {
                "order", "pedido", "ऑर्डर",
                "status", "track", "tracking",
                "delivery", "delivered", "delayed",
                "where", "donde", "dónde",
                "कुठे", "कधी", "kab", "kahan"
            },

            "refund": {
                "refund", "reembolso",
                "परतावा", "return",
                "money", "paise"
            },

            "payment": {
                "payment", "pago",
                "पेमेंट", "paid", "charge",
                "charged", "transaction"
            },

            "product_issue": {
                "product", "producto",
                "उत्पादन", "damaged",
                "broken", "wrong", "defective",
                "खराब"
            },

            "general": {
                "help", "ayuda", "मदत",
                "please", "problem",
                "issue", "question",
                "need"
            }
        }

    # ========================================================
    # NORMALIZATION
    # ========================================================

    def normalize_text(self, text: str) -> str:

        text = unicodedata.normalize(
            "NFKC",
            str(text)
        )

        text = re.sub(
            r"\s+",
            " ",
            text.strip()
        )

        corrections = {
            "ordr": "order",
            "oder": "order",
            "orderr": "order",
            "refnd": "refund",
            "refun": "refund",
            "paymnt": "payment",
            "pament": "payment",
            "delivry": "delivery",
            "delvery": "delivery",
            "prodct": "product",
            "shippment": "shipment"
        }

        words = []

        for word in text.split():

            clean = re.sub(
                r"[^\w\u0900-\u097F-]",
                "",
                word.lower()
            )

            words.append(
                corrections.get(
                    clean,
                    word
                )
            )

        return " ".join(words)

    # ========================================================
    # LANGUAGE DETECTION
    # ========================================================

    def detect_language(self, text: str):

        text = self.normalize_text(text)

        lower = text.lower()

        # ----------------------------------------------------
        # MARATHI / HINDI SCRIPT
        # ----------------------------------------------------

        devanagari_words = re.findall(
            r"[\u0900-\u097F]+",
            text
        )

        if devanagari_words:

            marathi_markers = [
                "माझा", "माझी", "माझे",
                "मला", "कुठे", "पाहिजे",
                "आहे", "आहेत", "नाही",
                "मदत", "आणि", "कसे"
            ]

            hindi_markers = [
                "मेरा", "मेरी", "मेरे",
                "मुझे", "कहाँ", "कब",
                "है", "हैं", "नहीं",
                "मदद", "और", "कैसे"
            ]

            marathi_score = sum(
                1 for word in marathi_markers
                if word in lower
            )

            hindi_score = sum(
                1 for word in hindi_markers
                if word in lower
            )

            if marathi_score > hindi_score:
                return "marathi", 0.90

            if hindi_score > marathi_score:
                return "hindi", 0.90

            # Generic Devanagari.
            # Hindi is used as fallback because it is one
            # of the configured supported languages.
            return "hindi", 0.60

        # ----------------------------------------------------
        # LATIN LANGUAGES
        # ----------------------------------------------------

        tokens = set(
            re.findall(
                r"[a-zA-Z]+",
                lower
            )
        )

        scores = {}

        for language, words in self.language_words.items():

            scores[language] = len(
                tokens.intersection(words)
            )

        # ----------------------------------------------------
        # SPECIAL STRONG PATTERNS
        # ----------------------------------------------------

        # Hindi transliteration
        hindi_transliterated = {
            "mera", "meri", "mere",
            "mujhe", "kab", "kahan",
            "hai", "chahiye", "nahi",
            "paise", "madad"
        }

        hindi_hits = len(
            tokens.intersection(
                hindi_transliterated
            )
        )

        if hindi_hits >= 2:
            scores["hindi"] += 3

        # Spanish
        spanish_markers = {
            "hola", "pedido", "reembolso",
            "quiero", "necesito", "ayuda",
            "donde", "cuando"
        }

        if len(
            tokens.intersection(
                spanish_markers
            )
        ) >= 1:
            scores["spanish"] += 2

        # English strong pattern
        english_markers = {
            "where", "what", "when",
            "please", "my", "is",
            "want", "need"
        }

        if len(
            tokens.intersection(
                english_markers
            )
        ) >= 2:
            scores["english"] += 2

        # ----------------------------------------------------
        # BEST LANGUAGE
        # ----------------------------------------------------

        ranked = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        best_language, best_score = ranked[0]

        if best_score == 0:
            return "unknown", 0.0

        # Check genuine mixed-language message
        active = [
            language
            for language, score in scores.items()
            if score > 0
        ]

        if len(active) >= 2:

            # If one language clearly dominates,
            # return that language rather than incorrectly
            # marking normal messages as mixed.
            second_score = ranked[1][1]

            if best_score - second_score <= 1:
                return "mixed", 0.75

        # Valid language
        confidence = min(
            0.60 + (best_score * 0.08),
            0.98
        )

        return best_language, confidence

    # ========================================================
    # INTENT DETECTION
    # ========================================================

    def detect_intent(self, text: str):

        text = self.normalize_text(
            text
        ).lower()

        tokens = set(
            re.findall(
                r"[a-zA-Z\u0900-\u097F]+",
                text
            )
        )

        scores = {}

        for intent, words in self.intent_words.items():

            scores[intent] = len(
                tokens.intersection(words)
            )

        best_intent = max(
            scores,
            key=scores.get
        )

        best_score = scores[best_intent]

        if best_score == 0:

            return "unknown", 0.0

        confidence = min(
            0.60 + (best_score * 0.08),
            0.98
        )

        return best_intent, confidence

    # ========================================================
    # ENTITY EXTRACTION
    # ========================================================

    def extract_entities(self, text: str):

        entities = {
            "names": [],
            "order_ids": [],
            "dates": [],
            "product_codes": []
        }

        # ----------------------------------------------------
        # ORDER IDS
        # ----------------------------------------------------

        order_patterns = [
            r"\bORD[-_]?[A-Z0-9]+\b",
            r"\bORDER[-_]?[A-Z0-9]+\b"
        ]

        for pattern in order_patterns:

            matches = re.findall(
                pattern,
                text,
                flags=re.IGNORECASE
            )

            entities["order_ids"].extend(
                matches
            )

        entities["order_ids"] = list(
            dict.fromkeys(
                entities["order_ids"]
            )
        )

        # ----------------------------------------------------
        # DATES
        # ----------------------------------------------------

        date_patterns = [
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
            r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b"
        ]

        for pattern in date_patterns:

            matches = re.findall(
                pattern,
                text
            )

            entities["dates"].extend(
                matches
            )

        entities["dates"] = list(
            dict.fromkeys(
                entities["dates"]
            )
        )

        # ----------------------------------------------------
        # PRODUCT CODES
        # ----------------------------------------------------

        product_patterns = [
            r"\bSKU[-_]?[A-Z0-9]+\b",
            r"\bPROD[-_]?[A-Z0-9]+\b",
            r"\bP[-_]?[A-Z0-9]{3,}\b"
        ]

        for pattern in product_patterns:

            matches = re.findall(
                pattern,
                text,
                flags=re.IGNORECASE
            )

            entities["product_codes"].extend(
                matches
            )

        entities["product_codes"] = list(
            dict.fromkeys(
                entities["product_codes"]
            )
        )

        # ----------------------------------------------------
        # NAME
        # ----------------------------------------------------

        name_match = re.search(
            r"(?:name\s*(?:is|:)\s*)"
            r"([A-Za-z][A-Za-z .'-]{1,40})",
            text,
            flags=re.IGNORECASE
        )

        if name_match:

            entities["names"].append(
                name_match.group(1).strip()
            )

        return entities

    # ========================================================
    # MULTIPLE REQUESTS
    # ========================================================

    def split_requests(self, text: str):

        parts = re.split(
            r"\b(?:and also|also|plus|then)\b|[?;]+",
            text,
            flags=re.IGNORECASE
        )

        if len(parts) == 1:

            parts = re.split(
                r"\s+\band\b\s+",
                text,
                flags=re.IGNORECASE
            )

        requests = [
            part.strip()
            for part in parts
            if part.strip()
        ]

        return requests or [text.strip()]

    # ========================================================
    # CORRECTION DETECTION
    # ========================================================

    def detect_correction(self, text: str):

        patterns = [
            r"\bactually\b",
            r"\bcorrection\b",
            r"\bcorrect\b",
            r"\binstead\b",
            r"\bwrong\b",
            r"\bnot\b",
            r"\bchange\b",
            r"चूक",
            r"बरोबर",
            r"नाही",
            r"म्हणजे"
        ]

        lower = text.lower()

        return any(
            re.search(
                pattern,
                lower
            )
            for pattern in patterns
        )

    # ========================================================
    # CREATE SESSION
    # ========================================================

    def create_session(
        self,
        customer_id,
        session_id=None,
        now=None
    ):

        now = now or datetime.now()

        if session_id is None:

            session_id = (
                f"{customer_id}-{now.timestamp()}"
            )

        session = Session(
            session_id=session_id,
            customer_id=customer_id,
            last_activity=now
        )

        self.sessions[session_id] = session

        return session

    # ========================================================
    # GET SESSION
    # ========================================================

    def get_session(self, session_id):

        return self.sessions.get(
            session_id
        )

    # ========================================================
    # SESSION EXPIRY
    # ========================================================

    def check_session_expiry(
        self,
        session,
        now=None
    ):

        now = now or datetime.now()

        if session.last_activity is None:
            return False

        inactive = (
            now - session.last_activity
        )

        if inactive >= timedelta(
            minutes=self.config.inactivity_minutes
        ):

            self.end_session(
                session.session_id,
                now
            )

            return True

        return False

    # ========================================================
    # SUMMARY
    # ========================================================

    def create_summary(self, session):

        if not session.messages:

            return "No conversation history."

        recent = session.messages[
            -self.config.context_messages:
        ]

        return " | ".join(
            f"[{m.language}] "
            f"{m.intent}: "
            f"{m.text}"
            for m in recent
        )

    # ========================================================
    # END SESSION
    # ========================================================

    def end_session(
        self,
        session_id,
        now=None
    ):

        now = now or datetime.now()

        session = self.sessions.pop(
            session_id,
            None
        )

        if session is None:
            return None

        session.active = False
        session.ended_at = now
        session.summary = self.create_summary(
            session
        )

        self.closed_sessions[
            session_id
        ] = session

        return session

    # ========================================================
    # RESTORE SESSION
    # ========================================================

    def restore_session(
        self,
        session_id,
        now=None
    ):

        now = now or datetime.now()

        old = self.closed_sessions.get(
            session_id
        )

        if old is None:
            return None

        if old.ended_at is None:
            return None

        elapsed = (
            now - old.ended_at
        )

        # Restore within 24 hours
        if elapsed <= timedelta(
            hours=self.config.restore_hours
        ):

            old.active = True
            old.last_activity = now

            self.sessions[session_id] = old

            del self.closed_sessions[
                session_id
            ]

            return old

        # Beyond 24 hours -> new session
        del self.closed_sessions[
            session_id
        ]

        return self.create_session(
            customer_id=old.customer_id,
            session_id=session_id,
            now=now
        )

    # ========================================================
    # PROCESS MESSAGE
    # ========================================================

    def process_message(
        self,
        session_id,
        customer_id,
        text,
        now=None
    ):

        now = now or datetime.now()

        # ----------------------------------------------------
        # CUSTOMER SESSION ISOLATION
        # ----------------------------------------------------

        session = self.sessions.get(
            session_id
        )

        # Never allow another customer to use an existing
        # customer's session.
        if session is not None:

            if session.customer_id != customer_id:

                return {
                    "status": "session_isolation_error",
                    "message": (
                        "This session belongs to "
                        "another customer."
                    ),
                    "session_id": session_id
                }

        # ----------------------------------------------------
        # CREATE OR RESTORE SESSION
        # ----------------------------------------------------

        if session is None:

            if session_id in self.closed_sessions:

                old = self.closed_sessions[
                    session_id
                ]

                if old.customer_id != customer_id:

                    return {
                        "status":
                            "session_isolation_error",
                        "message": (
                            "This session belongs to "
                            "another customer."
                        ),
                        "session_id": session_id
                    }

                session = self.restore_session(
                    session_id,
                    now
                )

            if session is None:

                session = self.create_session(
                    customer_id,
                    session_id,
                    now
                )

        # ----------------------------------------------------
        # EXPIRE ACTIVE SESSION
        # ----------------------------------------------------

        if session.active:

            if self.check_session_expiry(
                session,
                now
            ):

                session = self.restore_session(
                    session_id,
                    now
                )

                if session is None:

                    session = self.create_session(
                        customer_id,
                        session_id,
                        now
                    )

        # ----------------------------------------------------
        # ANALYZE MESSAGE
        # ----------------------------------------------------

        normalized = self.normalize_text(
            text
        )

        language, language_confidence = (
            self.detect_language(
                normalized
            )
        )

        intent, intent_confidence = (
            self.detect_intent(
                normalized
            )
        )

        entities = self.extract_entities(
            text
        )

        requests = self.split_requests(
            text
        )

        corrected = self.detect_correction(
            text
        )

        # ----------------------------------------------------
        # LOW LANGUAGE CONFIDENCE
        # ----------------------------------------------------

        if language == "unknown":

            return {
                "status":
                    "clarification_required",

                "message":
                    "Please clarify your language.",

                "language":
                    language,

                "language_confidence":
                    language_confidence,

                "intent":
                    intent,

                "intent_confidence":
                    intent_confidence,

                "entities":
                    entities
            }

        # ----------------------------------------------------
        # LOW INTENT CONFIDENCE
        # ----------------------------------------------------

        if intent == "unknown" or (
            intent_confidence
            < self.config.intent_threshold
        ):

            return {
                "status":
                    "clarification_required",

                "message":
                    "Please clarify your request.",

                "language":
                    language,

                "language_confidence":
                    language_confidence,

                "intent":
                    intent,

                "intent_confidence":
                    intent_confidence,

                "entities":
                    entities
            }

        # ----------------------------------------------------
        # STORE MESSAGE
        # ----------------------------------------------------

        message = Message(
            text=text,
            language=language,
            intent=intent,
            timestamp=now,
            confidence=min(
                language_confidence,
                intent_confidence
            )
        )

        session.messages.append(
            message
        )

        # Keep last 10 messages
        session.messages = session.messages[
            -self.config.context_messages:
        ]

        session.last_activity = now

        session.summary = self.create_summary(
            session
        )

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        return {
            "status": "success",

            "session_id":
                session.session_id,

            "customer_id":
                session.customer_id,

            "language":
                language,

            "language_confidence":
                language_confidence,

            "intent":
                intent,

            "intent_confidence":
                intent_confidence,

            "entities":
                entities,

            "requests":
                requests,

            "corrected_information":
                corrected,

            "context_messages":
                len(session.messages),

            "message":
                "Message processed successfully."
        }