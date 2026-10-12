# task5/evidence_processor.py

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import hashlib
import json
import os
import re
import shutil
import time


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class EvidenceData:
    order_id: Optional[str] = None
    date: Optional[str] = None
    amount: Optional[str] = None
    product: Optional[str] = None
    error_code: Optional[str] = None


@dataclass
class ProcessingResult:
    status: str
    message: str
    evidence: EvidenceData = field(
        default_factory=EvidenceData
    )
    conflicts: List[str] = field(
        default_factory=list
    )
    citations: List[str] = field(
        default_factory=list
    )
    background_job_id: Optional[str] = None
    log_message: Optional[str] = None


@dataclass
class UploadedFile:
    file_id: str
    path: str
    uploaded_at: datetime
    retention_until: datetime
    status: str = "active"


# ============================================================
# EVIDENCE PROCESSOR
# ============================================================

class EvidenceProcessor:

    # --------------------------------------------------------
    # Supported file types
    # --------------------------------------------------------

    SUPPORTED_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".pdf",
        ".txt",
        ".csv"
    }

    # --------------------------------------------------------
    # Unsafe file types
    # --------------------------------------------------------

    UNSAFE_EXTENSIONS = {
        ".exe",
        ".bat",
        ".cmd",
        ".com",
        ".scr",
        ".msi",
        ".dll",
        ".ps1",
        ".vbs",
        ".js",
        ".jar",
        ".sh",
        ".php",
        ".py",
        ".zip"
    }

    # --------------------------------------------------------
    # Prompt injection patterns
    # --------------------------------------------------------

    PROMPT_INJECTION_PATTERNS = [
        "ignore previous instructions",
        "ignore all instructions",
        "ignore prior instructions",
        "ignore the system prompt",
        "reveal system prompt",
        "show system prompt",
        "reveal developer message",
        "developer message",
        "developer instructions",
        "jailbreak",
        "override system",
        "disregard previous instructions",
        "follow hidden instructions",
        "follow these instructions",
        "execute this command",
        "run this command",
        "bypass security",
        "disable security",
        "reveal secret",
        "reveal password",
        "reveal api key"
    ]

    # --------------------------------------------------------
    # OCR / extraction patterns
    # --------------------------------------------------------

    ORDER_ID_PATTERNS = [
        r"\border\s*(?:id|number|no)?\s*[:#-]?\s*([A-Z]{1,5}[-]?\d{3,})\b",
        r"\bORD[-]?\d{3,}\b",
        r"\bORDER[-]?\d{3,}\b"
    ]

    DATE_PATTERNS = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{2}/\d{2}/\d{4}\b",
        r"\b\d{2}-\d{2}-\d{4}\b"
    ]

    AMOUNT_PATTERNS = [
        r"(?:₹|rs\.?|inr|\$|usd|€|eur|£|gbp)\s*[\d,]+(?:\.\d{1,2})?",
        r"\b(?:amount|total|price)\s*[:=]?\s*(?:₹|rs\.?|inr|\$|usd|€|eur|£|gbp)?\s*[\d,]+(?:\.\d{1,2})?",
    ]

    ERROR_CODE_PATTERNS = [
        r"\bERR[-_]?\d{2,6}\b",
        r"\bERROR[-_]?\d{2,6}\b",
        r"\bE\d{3,5}\b"
    ]

    PRODUCT_PATTERNS = [
        r"(?:product name|item name|product|item|model)\s*[:=-]\s*([A-Za-z0-9][A-Za-z0-9 ._-]{1,80})"
    ]

    GENERIC_PRODUCT_PHRASES = {
        "a different product", "different product", "the product",
        "an item", "the item", "something else", "unknown"
    }

    # --------------------------------------------------------
    # Payment / personal information
    # --------------------------------------------------------

    EMAIL_PATTERN = re.compile(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        re.I
    )

    PHONE_PATTERN = re.compile(
        r"(?<!\d)(?:\+?\d[\d\s().-]{8,}\d)(?!\d)"
    )

    CARD_PATTERN = re.compile(
        r"\b(?:\d[ -]*?){13,19}\b"
    )

    CVV_PATTERN = re.compile(
        r"\b(?:cvv|cvc|security code)\s*[:=-]?\s*\d{3,4}\b",
        re.I
    )

    # --------------------------------------------------------
    # Constructor
    # --------------------------------------------------------

    def __init__(
        self,
        retention_seconds: int = 86400,
        processing_limit_seconds: float = 30.0
    ):

        self.retention_seconds = max(
            0,
            int(retention_seconds)
        )

        self.processing_limit_seconds = float(
            processing_limit_seconds
        )

        self.uploads: Dict[
            str,
            UploadedFile
        ] = {}

        self.background_queue: List[
            Dict
        ] = []

        self.logs: List[str] = []

        self._job_counter = 0

    # ========================================================
    # FILE VALIDATION
    # ========================================================

    def validate_file(
        self,
        file_path
    ) -> Tuple[bool, str]:

        path = Path(file_path)

        if not path.exists():
            return False, "File does not exist."

        if not path.is_file():
            return False, "Uploaded path is not a file."

        extension = path.suffix.lower()

        if extension in self.UNSAFE_EXTENSIONS:
            return False, "Unsafe file type rejected."

        if extension not in self.SUPPORTED_EXTENSIONS:
            return False, "Unsupported file type."

        # Reject unexpectedly large files before OCR or PDF parsing.
        try:
            if path.stat().st_size > 10 * 1024 * 1024:
                return False, "File is larger than the 10 MB upload limit."
            if path.stat().st_size == 0:
                return False, "The uploaded file is empty."
        except OSError:
            return False, "Unable to inspect uploaded file safely."

        # Verify binary file signatures so a renamed executable or
        # unrelated binary cannot be treated as an image/PDF.
        if extension == ".pdf":
            try:
                with path.open("rb") as stream:
                    if b"%PDF-" not in stream.read(1024):
                        return False, "The file does not appear to be a valid PDF."
            except OSError:
                return False, "Unable to inspect uploaded PDF safely."
        if extension in {".png", ".jpg", ".jpeg", ".webp"}:
            try:
                from PIL import Image
                with Image.open(path) as image:
                    image.verify()
            except Exception:
                return False, "The image file is invalid or corrupted."

        # Basic suspicious content check for
        # text-like files.
        if extension in {
            ".txt",
            ".csv"
        }:

            try:

                text = path.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )

                if self.contains_prompt_injection(
                    text
                ):
                    return False, (
                        "Malicious instructions detected."
                    )

            except Exception:
                return False, (
                    "Unable to safely inspect file."
                )

        return True, "File is safe."

    # ========================================================
    # PROMPT INJECTION
    # ========================================================

    def contains_prompt_injection(
        self,
        text: str
    ) -> bool:

        if not text:
            return False

        normalized = re.sub(
            r"\s+",
            " ",
            str(text).lower()
        ).strip()

        for pattern in self.PROMPT_INJECTION_PATTERNS:

            if pattern in normalized:
                return True

        return False

    # ========================================================
    # IMAGE QUALITY
    # ========================================================

    def check_image_quality(
        self,
        file_path
    ) -> Tuple[bool, str]:

        path = Path(file_path)

        try:

            from PIL import Image

            image = Image.open(path)

            width, height = image.size

            # Very small images are unreliable.
            if width < 100 or height < 100:

                return False, (
                    "Image resolution is too low."
                )

            # Try a basic variance test.
            try:

                import numpy as np

                gray = image.convert(
                    "L"
                )

                array = np.asarray(
                    gray,
                    dtype=float
                )

                variance = float(
                    array.var()
                )

                # Extremely low variance usually
                # means blank / heavily blurred image.
                if variance < 30:
                    return False, (
                        "Image quality is too low or "
                        "image appears blank."
                    )

                # Low edge variance is a stronger blur signal than
                # brightness variance alone. Avoid claiming OCR accuracy.
                try:
                    from PIL import ImageFilter
                    edges = gray.filter(ImageFilter.FIND_EDGES)
                    edge_array = np.asarray(edges, dtype=float)
                    if float(edge_array.var()) < 8:
                        return False, (
                            "Image appears blurred. Please upload a sharper image."
                        )
                except Exception:
                    pass

            except Exception:
                pass

            return True, "Image quality acceptable."

        except ImportError:

            # If PIL is unavailable, don't falsely
            # claim that the image is bad.
            return True, (
                "Image accepted; optional quality "
                "inspection unavailable."
            )

        except Exception:

            return False, (
                "Unable to inspect image quality."
            )

    # ========================================================
    # OCR
    # ========================================================

    def extract_text(
        self,
        file_path
    ) -> str:

        path = Path(file_path)

        extension = path.suffix.lower()

        # ----------------------------------------------------
        # Text files
        # ----------------------------------------------------

        if extension in {
            ".txt",
            ".csv"
        }:

            return path.read_text(
                encoding="utf-8",
                errors="ignore"
            )

        # ----------------------------------------------------
        # PDF
        # ----------------------------------------------------

        if extension == ".pdf":

            # Try pypdf first.
            try:

                from pypdf import PdfReader

                reader = PdfReader(
                    str(path)
                )

                pages = []

                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text)

                extracted = "\n".join(pages).strip()
                if extracted:
                    return extracted

                # Scanned PDFs often have no text layer. Try rendering their
                # pages and OCRing them when optional PyMuPDF + Tesseract are
                # installed. If not available, the caller asks for a clearer
                # supported file instead of inventing fields.
                try:
                    import fitz
                    import pytesseract
                    from PIL import Image
                    import io
                    ocr_pages = []
                    with fitz.open(str(path)) as pdf_document:
                        for pdf_page in pdf_document:
                            pixmap = pdf_page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
                            page_text = pytesseract.image_to_string(image)
                            if page_text.strip():
                                ocr_pages.append(page_text)
                    return "\n".join(ocr_pages)
                except Exception:
                    return ""

            except ImportError:
                return ""

            except Exception:
                return ""

        # ----------------------------------------------------
        # Image OCR
        # ----------------------------------------------------

        if extension in {
            ".png",
            ".jpg",
            ".jpeg",
            ".webp"
        }:

            try:

                import pytesseract
                from PIL import Image

                image = Image.open(path)

                return pytesseract.image_to_string(
                    image
                )

            except ImportError:
                return ""

            except Exception:
                return ""

        return ""

    # ========================================================
    # EXTRACT ORDER ID
    # ========================================================

    def extract_order_id(
        self,
        text: str
    ) -> Optional[str]:

        if not text:
            return None

        for pattern in self.ORDER_ID_PATTERNS:

            match = re.search(
                pattern,
                text,
                re.I
            )

            if match:

                value = (
                    match.group(1)
                    if match.lastindex
                    else match.group(0)
                )

                return value.strip()

        return None

    # ========================================================
    # EXTRACT DATE
    # ========================================================

    def extract_date(
        self,
        text: str
    ) -> Optional[str]:

        if not text:
            return None

        for pattern in self.DATE_PATTERNS:

            match = re.search(
                pattern,
                text
            )

            if match:
                return match.group(0)

        return None

    # ========================================================
    # EXTRACT AMOUNT
    # ========================================================

    def extract_amount(
        self,
        text: str
    ) -> Optional[str]:

        if not text:
            return None

        for pattern in self.AMOUNT_PATTERNS:

            match = re.search(
                pattern,
                text,
                re.I
            )

            if match:
                return match.group(0).strip()

        return None

    # ========================================================
    # EXTRACT PRODUCT
    # ========================================================

    def extract_product(
        self,
        text: str
    ) -> Optional[str]:

        if not text:
            return None

        for pattern in self.PRODUCT_PATTERNS:

            match = re.search(
                pattern,
                text,
                re.I
            )

            if match:
                return match.group(1).strip()

        return None

    # ========================================================
    # EXTRACT ERROR CODE
    # ========================================================

    def extract_error_code(
        self,
        text: str
    ) -> Optional[str]:

        if not text:
            return None

        for pattern in self.ERROR_CODE_PATTERNS:

            match = re.search(
                pattern,
                text,
                re.I
            )

            if match:
                return match.group(0).upper()

        return None

    # ========================================================
    # EXTRACT ALL EVIDENCE
    # ========================================================

    def extract_evidence(
        self,
        text: str
    ) -> EvidenceData:

        return EvidenceData(
            order_id=self.extract_order_id(
                text
            ),
            date=self.extract_date(
                text
            ),
            amount=self.extract_amount(
                text
            ),
            product=self.extract_product(
                text
            ),
            error_code=self.extract_error_code(
                text
            )
        )

    # ========================================================
    # NORMALIZE AMOUNT
    # ========================================================

    @staticmethod
    def normalize_amount(
        value: Optional[str]
    ) -> Optional[float]:

        if not value:
            return None

        cleaned = re.sub(
            r"[^\d.]",
            "",
            value
        )

        try:
            return float(cleaned)
        except ValueError:
            return None

    # ========================================================
    # COMPARE EVIDENCE
    # ========================================================

    def compare_evidence(
        self,
        message: str,
        evidence: EvidenceData
    ) -> List[str]:

        conflicts = []

        if not message:
            return conflicts

        message_evidence = (
            self.extract_evidence(message)
        )

        # ----------------------------------------------------
        # Order ID
        # ----------------------------------------------------

        if (
            message_evidence.order_id
            and evidence.order_id
            and
            message_evidence.order_id.lower()
            != evidence.order_id.lower()
        ):

            conflicts.append(
                "Order ID does not match."
            )

        # ----------------------------------------------------
        # Date
        # ----------------------------------------------------

        if (
            message_evidence.date
            and evidence.date
            and
            message_evidence.date
            != evidence.date
        ):

            conflicts.append(
                "Date does not match."
            )

        # ----------------------------------------------------
        # Amount
        # ----------------------------------------------------

        message_amount = (
            self.normalize_amount(
                message_evidence.amount
            )
        )

        evidence_amount = (
            self.normalize_amount(
                evidence.amount
            )
        )

        if (
            message_amount is not None
            and evidence_amount is not None
            and message_amount != evidence_amount
        ):

            conflicts.append(
                "Amount does not match."
            )

        # ----------------------------------------------------
        # Product
        # ----------------------------------------------------

        if (
            message_evidence.product
            and evidence.product
            and
            message_evidence.product.lower()
            != evidence.product.lower()
        ):

            conflicts.append(
                "Product information does not match."
            )

        # If the customer describes a received/delivered product in
        # natural language, compare that claim with the invoice product.
        # Generic phrases are ignored rather than guessed.
        if evidence.product and not message_evidence.product:
            received = re.search(
                r"\b(?:received|got|delivered|sent)\s+(?:an?\s+|the\s+)?([a-z][a-z0-9 -]{1,45})",
                message,
                re.I,
            )
            if received:
                mentioned = received.group(1).strip(" .,!?:;").lower()
                mentioned = re.split(r"\b(?:but|instead|and|on|for|with)\b", mentioned)[0].strip()
                invoice_product = evidence.product.lower().strip()
                if mentioned and mentioned not in self.GENERIC_PRODUCT_PHRASES:
                    if mentioned not in invoice_product and invoice_product not in mentioned:
                        conflicts.append("Product information may not match the customer message; please confirm the received product.")

        # ----------------------------------------------------
        # Error code
        # ----------------------------------------------------

        if (
            message_evidence.error_code
            and evidence.error_code
            and
            message_evidence.error_code.lower()
            != evidence.error_code.lower()
        ):

            conflicts.append(
                "Error code does not match."
            )

        return conflicts

    # ========================================================
    # MISSING EVIDENCE
    # ========================================================

    def missing_required_evidence(
        self,
        evidence: EvidenceData,
        required_fields: Optional[List[str]] = None
    ) -> List[str]:

        if required_fields is None:

            required_fields = [
                "order_id"
            ]

        missing = []

        for field_name in required_fields:

            value = getattr(
                evidence,
                field_name,
                None
            )

            if value is None or str(value).strip() == "":
                missing.append(field_name)

        return missing

    # ========================================================
    # MASK PERSONAL/PAYMENT INFORMATION
    # ========================================================

    def mask_sensitive_data(
        self,
        text: str
    ) -> str:

        if not text:
            return text

        masked = str(text)

        # Email
        masked = self.EMAIL_PATTERN.sub(
            "[EMAIL_MASKED]",
            masked
        )

        # CVV
        masked = self.CVV_PATTERN.sub(
            "[CVV_MASKED]",
            masked
        )

        # Card numbers
        masked = self.CARD_PATTERN.sub(
            "[CARD_MASKED]",
            masked
        )

        # Phone numbers
        masked = self.PHONE_PATTERN.sub(
            "[PHONE_MASKED]",
            masked
        )

        return masked

    # ========================================================
    # SAFE LOGGING
    # ========================================================

    def log(
        self,
        message: str
    ) -> str:

        safe_message = (
            self.mask_sensitive_data(
                message
            )
        )

        self.logs.append(
            safe_message
        )

        return safe_message

    # ========================================================
    # UPLOAD REGISTRATION
    # ========================================================

    def register_upload(
        self,
        file_path,
        now: Optional[datetime] = None
    ) -> UploadedFile:

        if now is None:
            now = datetime.now()

        path = Path(file_path)

        file_id = hashlib.sha256(
            str(path.absolute()).encode()
        ).hexdigest()[:16]

        upload = UploadedFile(
            file_id=file_id,
            path=str(path),
            uploaded_at=now,
            retention_until=(
                now
                + timedelta(
                    seconds=self.retention_seconds
                )
            )
        )

        self.uploads[file_id] = upload

        return upload

    # ========================================================
    # EXPIRED FILE CHECK
    # ========================================================

    def is_expired(
        self,
        upload: UploadedFile,
        now: Optional[datetime] = None
    ) -> bool:

        if now is None:
            now = datetime.now()

        return now >= upload.retention_until

    # ========================================================
    # DELETE EXPIRED UPLOADS
    # ========================================================

    def delete_expired_files(
        self,
        now: Optional[datetime] = None
    ) -> int:

        if now is None:
            now = datetime.now()

        deleted = 0

        for file_id, upload in list(
            self.uploads.items()
        ):

            if not self.is_expired(
                upload,
                now
            ):
                continue

            path = Path(
                upload.path
            )

            try:

                if path.exists():

                    if path.is_file():
                        path.unlink()

                    elif path.is_dir():
                        shutil.rmtree(path)

                upload.status = "deleted"

                del self.uploads[file_id]

                deleted += 1

            except OSError:

                upload.status = (
                    "deletion_failed"
                )

        return deleted

    # ========================================================
    # BACKGROUND QUEUE
    # ========================================================

    def _create_background_job(
        self,
        file_path,
        message: str
    ) -> str:

        self._job_counter += 1

        job_id = (
            f"JOB-{self._job_counter:05d}"
        )

        job = {
            "job_id": job_id,
            "file_path": str(file_path),
            "message": message,
            "status": "queued",
            "created_at": datetime.now().isoformat()
        }

        self.background_queue.append(
            job
        )

        return job_id

    # ========================================================
    # CUSTOMER NOTIFICATION
    # ========================================================

    def background_notification(
        self,
        job_id: str
    ) -> str:

        return (
            f"Processing is taking longer than "
            f"30 seconds. Your request has been "
            f"moved to background processing. "
            f"Job ID: {job_id}"
        )

    # ========================================================
    # PROCESS EVIDENCE
    # ========================================================

    def process(
        self,
        message: str,
        file_path=None,
        required_fields: Optional[List[str]] = None,
        simulated_processing_seconds: float = 0.0,
        product: Optional[str] = None
    ) -> ProcessingResult:

        # ----------------------------------------------------
        # Message-only request
        # ----------------------------------------------------

        if file_path is None:

            evidence = self.extract_evidence(
                message
            )

            return ProcessingResult(
                status="completed",
                message=(
                    "Message analysed successfully."
                ),
                evidence=evidence,
                log_message=self.log(
                    message
                )
            )

        # ----------------------------------------------------
        # Validate file
        # ----------------------------------------------------

        valid, reason = self.validate_file(
            file_path
        )

        if not valid:

            return ProcessingResult(
                status="rejected",
                message=reason,
                log_message=self.log(
                    "File rejected: " + reason
                )
            )

        # ----------------------------------------------------
        # Register upload once; preserve its original retention deadline.
        # Re-registering the same file must not extend its retention.
        # ----------------------------------------------------

        normalized_path = str(Path(file_path).resolve())
        upload = next(
            (item for item in self.uploads.values()
             if str(Path(item.path).resolve()) == normalized_path),
            None,
        )
        if upload is None:
            upload = self.register_upload(file_path)

        # ----------------------------------------------------
        # Expired file check
        # ----------------------------------------------------

        if self.is_expired(upload):

            expired_path = Path(upload.path)
            try:
                if expired_path.exists() and expired_path.is_file():
                    expired_path.unlink()
            except OSError:
                upload.status = "deletion_failed"
            else:
                upload.status = "deleted"
            self.uploads.pop(upload.file_id, None)

            return ProcessingResult(
                status="expired",
                message=(
                    "The uploaded file has expired. "
                    "Please upload the file again."
                ),
                log_message=self.log(
                    "Expired uploaded file rejected."
                )
            )

        # ----------------------------------------------------
        # Image quality
        # ----------------------------------------------------

        extension = (
            Path(file_path)
            .suffix
            .lower()
        )

        if extension in {
            ".png",
            ".jpg",
            ".jpeg",
            ".webp"
        }:

            quality_ok, quality_message = (
                self.check_image_quality(
                    file_path
                )
            )

            if not quality_ok:

                return ProcessingResult(
                    status="clarification_required",
                    message=(
                        "The image quality is too low "
                        "to reliably extract the required "
                        "information. Please upload a "
                        "clearer image."
                    ),
                    log_message=self.log(
                        quality_message
                    )
                )

        # ----------------------------------------------------
        # Start processing timer
        # ----------------------------------------------------

        start_time = time.monotonic()

        # Simulated delay is a test/demo control. Do not actually sleep for
        # the whole simulated duration; model elapsed time deterministically.
        # Real OCR/parsing time is still measured with a monotonic clock.
        if 0 < simulated_processing_seconds <= self.processing_limit_seconds:
            time.sleep(min(simulated_processing_seconds, 0.25))

        # ----------------------------------------------------
        # 30-second background processing rule
        # ----------------------------------------------------

        elapsed = time.monotonic() - start_time
        simulated_over_limit = (
            simulated_processing_seconds > self.processing_limit_seconds
        )

        if simulated_over_limit or elapsed > self.processing_limit_seconds:

            job_id = (
                self._create_background_job(
                    file_path,
                    message
                )
            )

            notification = (
                self.background_notification(
                    job_id
                )
            )

            return ProcessingResult(
                status="background",
                message=notification,
                background_job_id=job_id,
                log_message=self.log(
                    "File moved to background queue."
                )
            )

        # ----------------------------------------------------
        # Extract text
        # ----------------------------------------------------

        extracted_text = self.extract_text(
            file_path
        )

        # ----------------------------------------------------
        # Hidden instructions in OCR/PDF text
        # ----------------------------------------------------

        if self.contains_prompt_injection(
            extracted_text
        ):

            return ProcessingResult(
                status="rejected",
                message=(
                    "The uploaded file contains "
                    "unsafe instructions and has "
                    "been rejected."
                ),
                log_message=self.log(
                    "Prompt injection detected in "
                    "uploaded evidence."
                )
            )

        # ----------------------------------------------------
        # Missing OCR/evidence
        # ----------------------------------------------------

        if not extracted_text.strip():

            return ProcessingResult(
                status="clarification_required",
                message=(
                    "I could not reliably extract "
                    "evidence from the uploaded file. "
                    "Please upload a clearer image, "
                    "PDF or another supporting file."
                ),
                log_message=self.log(
                    "No reliable evidence extracted."
                )
            )

        # ----------------------------------------------------
        # Extract structured evidence
        # ----------------------------------------------------

        evidence = self.extract_evidence(
            extracted_text
        )

        # ----------------------------------------------------
        # Compare with customer message
        # ----------------------------------------------------

        conflicts = self.compare_evidence(
            message,
            evidence
        )

        if conflicts:

            return ProcessingResult(
                status="conflict",
                message=(
                    "The uploaded evidence conflicts "
                    "with the information in your message. "
                    "Please verify the information or "
                    "upload another supporting file."
                ),
                evidence=evidence,
                conflicts=conflicts,
                citations=[
                    Path(file_path).name
                ],
                log_message=self.log(
                    "Evidence conflict detected: "
                    + ", ".join(conflicts)
                )
            )

        # ----------------------------------------------------
        # Product validation
        # ----------------------------------------------------

        if product:

            if evidence.product:

                if (
                    product.lower()
                    not in evidence.product.lower()
                    and
                    evidence.product.lower()
                    not in product.lower()
                ):

                    return ProcessingResult(
                        status="conflict",
                        message=(
                            "The product information in "
                            "the uploaded evidence does "
                            "not match the requested product."
                        ),
                        evidence=evidence,
                        conflicts=[
                            "Product mismatch."
                        ],
                        citations=[
                            str(file_path)
                        ],
                        log_message=self.log(
                            "Product mismatch detected."
                        )
                    )

        # ----------------------------------------------------
        # Missing mandatory evidence
        # ----------------------------------------------------

        missing = (
            self.missing_required_evidence(
                evidence,
                required_fields
            )
        )

        if missing:

            return ProcessingResult(
                status="clarification_required",
                message=(
                    "Some required information could "
                    "not be verified from the uploaded "
                    "evidence. Please provide a clearer "
                    "file or another supporting document."
                ),
                evidence=evidence,
                citations=[
                    Path(file_path).name
                ],
                log_message=self.log(
                    "Missing evidence: "
                    + ", ".join(missing)
                )
            )

        # ----------------------------------------------------
        # Successful result
        # ----------------------------------------------------

        return ProcessingResult(
            status="completed",
            message=(
                "The uploaded evidence was processed "
                "successfully and matched the customer "
                "message."
            ),
            evidence=evidence,
            citations=[
                str(file_path)
            ],
            log_message=self.log(
                "Evidence processed successfully."
            )
        )

    # ========================================================
    # PROCESS QUEUED JOB
    # ========================================================

    def process_background_job(
        self,
        job_id: str
    ) -> Optional[ProcessingResult]:

        for job in self.background_queue:

            if job["job_id"] != job_id:
                continue

            job["status"] = "processing"

            result = self.process(
                message=job["message"],
                file_path=job["file_path"],
                simulated_processing_seconds=0
            )

            job["status"] = result.status

            return result

        return None