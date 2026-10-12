# task4/rag_assistant.py

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import csv
import json
import re
from typing import List, Optional, Tuple


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class RAGDocument:
    doc_id: str
    content: str
    product: str
    region: str
    access_level: str
    effective_date: date
    expiry_date: Optional[date]
    version: str
    doc_type: str
    source: str


@dataclass
class RAGAnswer:
    answer: str
    citations: List[str]
    needs_clarification: bool = False


# ============================================================
# RAG KNOWLEDGE ASSISTANT
# ============================================================

class RAGKnowledgeAssistant:

    ACCESS_LEVELS = {
        "public": 0,
        "customer": 1,
        "agent": 2,
        "admin": 3
    }

    MALICIOUS_PATTERNS = [
        "ignore previous instructions",
        "ignore all instructions",
        "ignore the system prompt",
        "reveal system prompt",
        "show system prompt",
        "developer message",
        "reveal developer instructions",
        "jailbreak",
        "override system",
        "disregard previous instructions",
        "follow these hidden instructions",
        "ignore prior instructions",
        "reveal hidden instructions"
    ]

    STOP_WORDS = {
        "the", "a", "an", "is", "are", "was", "were",
        "to", "of", "for", "on", "in", "and", "or",
        "can", "i", "me", "my", "what", "how", "do",
        "does", "please", "tell", "about", "current",
        "latest", "information", "date", "tell",
        "give", "show", "want", "know", "does"
    }

    POLICY_KEYWORDS = {
        "refund",
        "return",
        "cancellation",
        "warranty",
        "replacement",
        "eligibility",
        "shipping",
        "delivery",
        "payment",
        "subscription",
        "exchange"
    }

    def __init__(self):
        self.documents: List[RAGDocument] = []

    # ========================================================
    # DATE HELPERS
    # ========================================================

    @staticmethod
    def parse_date(value) -> Optional[date]:

        if value is None or value == "":
            return None

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        value = str(value).strip()

        formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
            "%m/%d/%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(
                    value,
                    fmt
                ).date()
            except ValueError:
                continue

        return None

    # ========================================================
    # DOCUMENT MANAGEMENT
    # ========================================================

    def add_document(
        self,
        document: RAGDocument
    ) -> bool:

        # Never store documents containing
        # known prompt-injection instructions.
        if self.contains_malicious_instruction(
            document.content
        ):
            return False

        # Reject malformed metadata instead of silently indexing an
        # unscoped document. Unknown access values are handled below.
        if not document.doc_id or not document.content or not document.source:
            return False
        if not isinstance(document.effective_date, date):
            return False
        if document.expiry_date and document.expiry_date < document.effective_date:
            return False

        # Prevent duplicate document IDs.
        for existing in self.documents:
            if existing.doc_id == document.doc_id:
                return False

        # Normalize invalid access levels.
        if (
            document.access_level is None
            or document.access_level.lower()
            not in self.ACCESS_LEVELS
        ):
            document.access_level = "customer"

        self.documents.append(document)

        return True

    # ========================================================
    # PROMPT INJECTION DETECTION
    # ========================================================

    def contains_malicious_instruction(
        self,
        text: str
    ) -> bool:

        if not text:
            return False

        normalized = re.sub(
            r"\s+",
            " ",
            text.lower()
        ).strip()

        for pattern in self.MALICIOUS_PATTERNS:
            if pattern in normalized:
                return True

        return False

    # ========================================================
    # ACCESS CONTROL
    # ========================================================

    def authorized(
        self,
        document: RAGDocument,
        user_access: str
    ) -> bool:

        user_level = self.ACCESS_LEVELS.get(
            str(user_access).lower(),
            -1
        )

        required_level = self.ACCESS_LEVELS.get(
            str(document.access_level).lower(),
            999
        )

        return user_level >= required_level

    # ========================================================
    # DATE APPLICABILITY
    # ========================================================

    def applicable_on(
        self,
        document: RAGDocument,
        requested_date: date
    ) -> bool:

        # Document cannot be used before
        # its effective date.
        if document.effective_date > requested_date:
            return False

        # Document cannot be used after expiry.
        if (
            document.expiry_date is not None
            and requested_date > document.expiry_date
        ):
            return False

        return True

    # ========================================================
    # EXTRACT DATE FROM QUERY
    # ========================================================

    def get_requested_date(
        self,
        query: str,
        as_of_date: Optional[date] = None
    ) -> date:
        """Resolve an explicitly requested historical date or current date.

        ``as_of_date`` supports deterministic runtime/simulated-date tests.
        An explicit date in the user's question always takes precedence.
        """
        patterns = [
            r"\b(20\d{2}-\d{2}-\d{2})\b",
            r"\b(\d{1,2}[/-]\d{1,2}[/-]20\d{2})\b",
            r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{1,2},?\s+20\d{2})\b",
            r"\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+20\d{2})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, query, flags=re.IGNORECASE)
            if match:
                parsed = self.parse_date(match.group(1))
                if parsed:
                    return parsed
        return as_of_date or date.today()

    # ========================================================
    # TOKENIZATION
    # ========================================================

    def tokenize(
        self,
        text: str
    ) -> set:

        words = re.findall(
            r"[a-zA-Z0-9]+",
            str(text).lower()
        )

        return {
            word
            for word in words
            if word not in self.STOP_WORDS
            and len(word) > 1
            and not re.fullmatch(
                r"\d{4}",
                word
            )
        }

    # ========================================================
    # SIMILARITY
    # ========================================================

    def similarity(
        self,
        query: str,
        document: RAGDocument
    ) -> float:

        query_words = self.tokenize(query)

        document_words = self.tokenize(
            document.content
        )

        if not query_words:
            return 0.0

        if not document_words:
            return 0.0

        overlap = (
            query_words
            .intersection(document_words)
        )

        return len(overlap) / len(query_words)

    # ========================================================
    # CONTEXT MATCHING
    # ========================================================

    def matches_context(
        self,
        query: str,
        document: RAGDocument,
        product: Optional[str] = None,
        region: Optional[str] = None
    ) -> bool:

        # Explicit product supplied by caller.
        if product:

            if (
                document.product.lower() != "all"
                and document.product.lower()
                != product.lower()
            ):
                return False

        # Explicit region supplied by caller.
        if region:

            if (
                document.region.lower() != "global"
                and document.region.lower()
                != region.lower()
            ):
                return False

        return True

    # ========================================================
    # POLICY CHECK
    # ========================================================

    def is_policy(
        self,
        document: RAGDocument
    ) -> bool:

        return (
            str(document.doc_type).lower()
            == "policy"
        )

    # ========================================================
    # VERSION NUMBER
    # ========================================================

    @staticmethod
    def version_number(
        version: str
    ) -> int:

        match = re.search(
            r"\d+",
            str(version)
        )

        if match:
            return int(match.group())

        return 0

    # ========================================================
    # SELECT LATEST APPLICABLE POLICY
    # ========================================================

    def select_latest_policy(
        self,
        documents: List[RAGDocument],
        query: str
    ) -> List[RAGDocument]:

        policies = [
            doc
            for doc in documents
            if self.is_policy(doc)
        ]

        if not policies:
            return documents

        query_words = self.tokenize(query)

        # Calculate relevance of each policy.
        scored = []

        for doc in policies:

            doc_words = self.tokenize(
                doc.content
            )

            overlap = query_words.intersection(
                doc_words
            )

            score = len(overlap)

            scored.append(
                (doc, score)
            )

        # Only keep policies relevant to the query.
        relevant_policies = [
            doc
            for doc, score in scored
            if score > 0
        ]

        if not relevant_policies:
            return [
                doc
                for doc in documents
                if not self.is_policy(doc)
            ]

        # Group by product + region.
        groups = {}

        for doc in relevant_policies:

            # Resolve conflicts only within the same product, region,
            # and policy topic. A newer warranty policy must not hide
            # an older-but-still-active refund policy.
            query_topics = [
                keyword for keyword in self.POLICY_KEYWORDS
                if keyword in query.lower()
            ]
            doc_text = (doc.content + " " + doc.doc_type).lower()
            topic = next(
                (keyword for keyword in query_topics if keyword in doc_text),
                next(
                    (keyword for keyword in sorted(self.POLICY_KEYWORDS, key=len, reverse=True)
                     if keyword in doc_text),
                    str(doc.doc_type).lower()
                )
            )
            key = (
                str(doc.product).lower(),
                str(doc.region).lower(),
                topic
            )

            groups.setdefault(
                key,
                []
            ).append(doc)

        selected = []

        for docs in groups.values():

            docs.sort(
                key=lambda d: (
                    d.effective_date,
                    self.version_number(
                        d.version
                    )
                ),
                reverse=True
            )

            selected.append(
                docs[0]
            )

        non_policies = [
            doc
            for doc in documents
            if not self.is_policy(doc)
        ]

        return selected + non_policies

    # ========================================================
    # RETRIEVE
    # ========================================================

    def retrieve(
        self,
        query: str,
        user_access: str = "customer",
        product: Optional[str] = None,
        region: Optional[str] = None,
        as_of_date: Optional[date] = None
    ) -> List[Tuple[RAGDocument, float]]:

        requested_date = self.get_requested_date(query, as_of_date=as_of_date)

        candidates = []

        query_lower = query.lower()

        query_words = self.tokenize(query)

        # If the query explicitly names a product or region present in
        # metadata, do not mix in another product/region's documents.
        normalized_query = query.lower()
        known_products = {
            str(doc.product).strip().lower() for doc in self.documents
            if str(doc.product).strip().lower() not in {"", "all", "global"}
        }
        known_regions = {
            str(doc.region).strip().lower() for doc in self.documents
            if str(doc.region).strip().lower() not in {"", "all", "global"}
        }
        mentioned_products = {value for value in known_products if value in normalized_query}
        mentioned_regions = {value for value in known_regions if value in normalized_query}
        effective_product = product.strip().lower() if product else (next(iter(mentioned_products)) if len(mentioned_products) == 1 else None)
        effective_region = region.strip().lower() if region else (next(iter(mentioned_regions)) if len(mentioned_regions) == 1 else None)

        for document in self.documents:

            # ------------------------------------------------
            # 1. Ignore malicious documents
            # ------------------------------------------------

            if self.contains_malicious_instruction(
                document.content
            ):
                continue

            # ------------------------------------------------
            # 2. Access control
            # ------------------------------------------------

            if not self.authorized(
                document,
                user_access
            ):
                continue

            # ------------------------------------------------
            # 3. Date control
            # ------------------------------------------------

            if not self.applicable_on(
                document,
                requested_date
            ):
                continue

            # ------------------------------------------------
            # 4. Product / region
            # ------------------------------------------------

            if not self.matches_context(
                query,
                document,
                effective_product,
                effective_region
            ):
                continue

            if mentioned_products and not product:
                if document.product.lower() not in {"all", "global"} and document.product.lower() not in mentioned_products:
                    continue
            if mentioned_regions and not region:
                if document.region.lower() not in {"all", "global"} and document.region.lower() not in mentioned_regions:
                    continue

            # ------------------------------------------------
            # 5. Calculate similarity
            # ------------------------------------------------

            score = self.similarity(
                query,
                document
            )

            content_lower = (
                document.content.lower()
            )

            # ------------------------------------------------
            # 6. Exact meaningful keyword match
            # ------------------------------------------------

            keyword_matches = [
                keyword
                for keyword in self.POLICY_KEYWORDS
                if keyword in query_lower
                and keyword in content_lower
            ]

            # ------------------------------------------------
            # 7. Product match
            # ------------------------------------------------

            product_match = False

            if document.product.lower() == "all":
                product_match = True

            elif document.product.lower() in query_lower:
                product_match = True

            # ------------------------------------------------
            # 8. Determine whether evidence exists
            # ------------------------------------------------

            has_meaningful_overlap = (
                len(
                    query_words.intersection(
                        self.tokenize(
                            document.content
                        )
                    )
                ) >= 2
            )

            has_policy_keyword = (
                len(keyword_matches) > 0
                and self.is_policy(document)
            )

            # Do not retrieve a random document just
            # because it shares one generic word.
            if not (
                has_meaningful_overlap
                or has_policy_keyword
                or (
                    product_match
                    and score >= 0.20
                )
            ):
                continue

            candidates.append(
                (
                    document,
                    score
                )
            )

        if not candidates:
            return []

        # ----------------------------------------------------
        # 9. Resolve conflicting policies
        # ----------------------------------------------------

        documents = [
            item[0]
            for item in candidates
        ]

        selected_documents = (
            self.select_latest_policy(
                documents,
                query
            )
        )

        selected_ids = {
            doc.doc_id
            for doc in selected_documents
        }

        candidates = [
            item
            for item in candidates
            if item[0].doc_id
            in selected_ids
        ]

        # ----------------------------------------------------
        # 10. Sort by relevance
        # ----------------------------------------------------

        candidates.sort(
            key=lambda item: item[1],
            reverse=True
        )

        return candidates

    # ========================================================
    # ANSWER
    # ========================================================

    def answer(
        self,
        query: str,
        user_access: str = "customer",
        product: Optional[str] = None,
        region: Optional[str] = None,
        as_of_date: Optional[date] = None
    ) -> RAGAnswer:

        # Treat instruction-override attempts in a user query as untrusted.
        if self.contains_malicious_instruction(query or ""):
            return RAGAnswer(
                answer=("I can only answer questions using authorised knowledge-base evidence. "
                        "Please rephrase your question without instructions to override system rules."),
                citations=[],
                needs_clarification=True
            )

        # Empty query
        if not query or not query.strip():

            return RAGAnswer(
                answer=(
                    "Please provide a question so I "
                    "can search the knowledge base."
                ),
                citations=[],
                needs_clarification=True
            )

        results = self.retrieve(
            query=query,
            user_access=user_access,
            product=product,
            region=region,
            as_of_date=as_of_date
        )

        # ----------------------------------------------------
        # No evidence
        # ----------------------------------------------------

        if not results:

            return RAGAnswer(
                answer=(
                    "I could not find reliable evidence "
                    "in the authorised knowledge base. "
                    "Please provide the product, region "
                    "or relevant date, or contact a "
                    "support agent."
                ),
                citations=[],
                needs_clarification=True
            )

        best_document, best_score = results[0]

        query_words = self.tokenize(
            query
        )

        document_words = self.tokenize(
            best_document.content
        )

        overlap = query_words.intersection(
            document_words
        )

        # ----------------------------------------------------
        # Strong policy match
        # ----------------------------------------------------

        policy_query = any(
            keyword in query.lower()
            for keyword in self.POLICY_KEYWORDS
        )

        strong_policy_match = (
            self.is_policy(best_document)
            and policy_query
            and len(overlap) >= 1
        )

        # ----------------------------------------------------
        # Evidence threshold
        # ----------------------------------------------------

        # A factual answer requires either:
        #
        # 1. at least 2 meaningful overlapping terms
        # OR
        # 2. a strong policy match
        #
        # This prevents unsupported answers.
        if (
            len(overlap) < 2
            and not strong_policy_match
        ):

            return RAGAnswer(
                answer=(
                    "I could not find sufficient evidence "
                    "to answer this question accurately. "
                    "Please provide more details or "
                    "contact a support agent."
                ),
                citations=[],
                needs_clarification=True
            )

        # ----------------------------------------------------
        # Build answer from retrieved evidence
        # ----------------------------------------------------

        answer_text = (
            best_document.content.strip()
        )

        # ----------------------------------------------------
        # Mandatory source citation
        # ----------------------------------------------------

        citation = (
            f"[Source: {best_document.source}, "
            f"version {best_document.version}]"
        )

        answer_text = (
            answer_text
            + "\n\n"
            + citation
        )

        return RAGAnswer(
            answer=answer_text,
            citations=[citation],
            needs_clarification=False
        )

    # ========================================================
    # CSV DATASET LOADER
    # ========================================================

    def load_csv_dataset(
        self,
        path,
        product: str = "all",
        region: str = "global",
        access_level: str = "customer"
    ) -> int:

        path = Path(path)

        if not path.exists():

            raise FileNotFoundError(
                f"Dataset not found: {path}"
            )

        count = 0

        with open(
            path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            for index, row in enumerate(reader):

                question = (
                    row.get("instruction")
                    or row.get("question")
                    or row.get("input")
                    or ""
                ).strip()

                response = (
                    row.get("response")
                    or row.get("answer")
                    or row.get("output")
                    or ""
                ).strip()

                if not question or not response:
                    continue

                content = (
                    f"Question: {question}\n"
                    f"Answer: {response}"
                )

                document = RAGDocument(
                    doc_id=(
                        f"{path.stem}-{index + 1}"
                    ),
                    content=content,
                    product=(
                        row.get("product")
                        or product
                    ),
                    region=(
                        row.get("region")
                        or region
                    ),
                    access_level=(
                        row.get("access_level")
                        or access_level
                    ),
                    effective_date=(
                        self.parse_date(
                            row.get(
                                "effective_date"
                            )
                        )
                        or date.min
                    ),
                    expiry_date=self.parse_date(
                        row.get("expiry_date")
                    ),
                    version=str(
                        row.get(
                            "version",
                            "1"
                        )
                    ),
                    doc_type=(
                        row.get("doc_type")
                        or "faq"
                    ),
                    source=(
                        row.get("source")
                        or (
                            f"{path.name}:"
                            f"row-{index + 2}"
                        )
                    )
                )

                if self.add_document(
                    document
                ):
                    count += 1

        return count

    # ========================================================
    # JSON DATASET LOADER
    # ========================================================

    def load_json_dataset(
        self,
        path,
        product: str = "all",
        region: str = "global",
        access_level: str = "customer"
    ) -> int:

        path = Path(path)

        if not path.exists():

            raise FileNotFoundError(
                f"Dataset not found: {path}"
            )

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, dict):

            data = data.get(
                "data",
                data.get(
                    "documents",
                    []
                )
            )

        count = 0

        for index, item in enumerate(data):

            question = (
                item.get("instruction")
                or item.get("question")
                or item.get("input")
                or ""
            ).strip()

            response = (
                item.get("response")
                or item.get("answer")
                or item.get("output")
                or ""
            ).strip()

            if not question or not response:
                continue

            content = (
                f"Question: {question}\n"
                f"Answer: {response}"
            )

            document = RAGDocument(
                doc_id=str(
                    item.get(
                        "doc_id",
                        f"{path.stem}-{index + 1}"
                    )
                ),
                content=content,
                product=item.get(
                    "product",
                    product
                ),
                region=item.get(
                    "region",
                    region
                ),
                access_level=item.get(
                    "access_level",
                    access_level
                ),
                effective_date=(
                    self.parse_date(
                        item.get(
                            "effective_date"
                        )
                    )
                    or date.min
                ),
                expiry_date=self.parse_date(
                    item.get("expiry_date")
                ),
                version=str(
                    item.get(
                        "version",
                        "1"
                    )
                ),
                doc_type=item.get(
                    "doc_type",
                    "faq"
                ),
                source=item.get(
                    "source",
                    f"{path.name}:item-{index + 1}"
                )
            )

            if self.add_document(
                document
            ):
                count += 1

        return count