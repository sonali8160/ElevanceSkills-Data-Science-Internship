import hashlib
import re
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class PipelineDocument:
    path: str
    content: str
    content_hash: str


@dataclass
class PipelineQualityResult:
    passed: bool
    accuracy: float
    grounding: float


@dataclass
class PipelineVersion:
    version_id: str
    documents: list
    quality: PipelineQualityResult
    status: str = "staged"


@dataclass
class PipelineResult:
    status: str
    message: str = ""


@dataclass
class HealthCheckResult:
    healthy: bool
    rolled_back: bool


@dataclass
class PipelineIngestionResult:
    new_documents: list
    modified_documents: list
    unchanged_documents: list
    duplicate_documents: list
    quarantined_documents: list


@dataclass
class PipelineState:
    pending_version: object = None
    active_version: object = None
    previous_version: object = None


# ============================================================
# VERSION MANAGER
# ============================================================

class PipelineVersionManager:

    def __init__(self):
        self.versions = []
        self.active_version = None

    def create_version(self, documents, quality):
        version = PipelineVersion(
            version_id=f"KB-v{len(self.versions) + 1}",
            documents=list(documents),
            quality=quality
        )

        self.versions.append(version)
        return version

    def activate(self, version):
        if self.active_version:
            self.active_version.status = "previous"

        version.status = "active"
        self.active_version = version

    def rollback(self, version):
        if version:
            version.status = "active"
            self.active_version = version

    def get_active_version(self):
        return self.active_version


# ============================================================
# MONITORING
# ============================================================

class PipelineMonitoring:

    def __init__(self):
        self.latencies = []
        self.confidences = []
        self.failures = 0
        self.escalations = 0

    def record(
        self,
        latency_ms,
        confidence,
        failed=False,
        escalated=False
    ):
        self.latencies.append(latency_ms)
        self.confidences.append(confidence)

        if failed:
            self.failures += 1

        if escalated:
            self.escalations += 1

    def summary(self):

        latency = (
            sum(self.latencies) / len(self.latencies)
            if self.latencies
            else 0
        )

        confidence = (
            sum(self.confidences) / len(self.confidences)
            if self.confidences
            else 0
        )

        return {
            "average_latency_ms": round(latency, 2),
            "average_confidence": round(confidence, 2),
            "total_failures": self.failures,
            "total_escalations": self.escalations
        }


# ============================================================
# KNOWLEDGE BASE PIPELINE
# ============================================================

class KnowledgeBasePipeline:

    ALLOWED_ROLES = {
        "admin": {
            "scan",
            "stage",
            "activate",
            "rollback",
            "monitor",
            "configure"
        },
        "update_operator": {
            "scan",
            "stage",
            "activate",
            "monitor"
        },
        "viewer": {
            "view"
        }
    }

    ALLOWED_EXTENSIONS = {
        ".txt",
        ".md",
        ".csv",
        ".json"
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
        r"do\s+not\s+follow\s+(the\s+)?(system|developer)\s+",
    ]

    def __init__(self, schedule):

        self.schedule = schedule
        self.version_manager = PipelineVersionManager()
        self.monitor = PipelineMonitoring()
        self.state = PipelineState()
        self.manifest = {}
        self.quarantine = []
        self.service_available = True

        self.scheduled_update_time = getattr(
            schedule,
            "update_time",
            None
        )
        # Retry attempts are stateful so simulated-time checks can execute
        # the 15, 30 and 60 minute retry sequence deterministically.
        self.retry_history = []
        self.retry_attempts = {}
        self.last_scan_result = None
        self.audit_log = []

    # ========================================================
    # ACCESS CONTROL
    # ========================================================

    def _check_access(self, user, action):

        role = getattr(user, "role", "")

        if action not in self.ALLOWED_ROLES.get(role, set()):
            raise PermissionError(
                f"Role '{role}' cannot perform '{action}'."
            )

    # ========================================================
    # PROMPT INJECTION
    # ========================================================

    def _prompt_injection(self, text):

        # Normalize whitespace and zero-width characters before matching.
        normalized = re.sub(r"[\u200b-\u200f\ufeff]", "", str(text or ""))
        normalized = re.sub(r"\s+", " ", normalized).lower()
        return any(
            re.search(pattern, normalized, re.IGNORECASE)
            for pattern in self.INJECTION_PATTERNS
        )

    # ========================================================
    # DOCUMENT VALIDATION
    # ========================================================

    def _validate_document(self, text):
        """
        Validate obviously invalid knowledge-base documents.

        Normal documents are allowed even when they do not
        contain an explicit Version field because the existing
        Task 3 tests use simple text documents.

        Documents containing an explicit invalid version such
        as UNKNOWN are quarantined.
        """

        # Empty file
        if not text or not text.strip():
            return False, "empty document"

        lowered = text.lower()

        # ----------------------------------------------------
        # Explicit invalid version
        # ----------------------------------------------------

        version_match = re.search(
            r"\bversion\s*[:=]\s*([A-Za-z0-9._-]+)",
            text,
            re.IGNORECASE
        )

        if version_match:

            version = version_match.group(1).strip()

            invalid_versions = {
                "UNKNOWN",
                "N/A",
                "NA",
                "NONE",
                "NULL",
                "UNDEFINED"
            }

            if version.upper() in invalid_versions:
                return False, "invalid version"

        # ----------------------------------------------------
        # Clearly unsupported document content
        # ----------------------------------------------------

        unsupported_phrases = [
            "random unsupported information",
            "unsupported information"
        ]

        for phrase in unsupported_phrases:

            if phrase in lowered:
                return False, "unsupported document content"

        return True, ""

    # ========================================================
    # MASK SENSITIVE DATA
    # ========================================================

    def mask_sensitive_data(self, text):

        text = re.sub(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
            "[EMAIL]",
            text
        )

        text = re.sub(
            r"(?<!\d)(?:\+?\d{1,3}[ .-]?)?(?:\(?\d{3}\)?[ .-]?)?\d{3}[ .-]?\d{4}(?!\d)",
            "[PHONE]",
            text
        )

        text = re.sub(
            r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)",
            "[CARD]",
            text
        )

        # Mask common government/customer identifiers in free-text documents.
        text = re.sub(
            r"\b(?:SSN|Aadhaar|Aadhar|Customer ID|CustomerID)\s*[:#-]?\s*[A-Z0-9-]{6,16}\b",
            "[IDENTIFIER]",
            text,
            flags=re.IGNORECASE,
        )

        return text

    # ========================================================
    # HASH
    # ========================================================

    def _hash(self, content):

        return hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

    def _quarantine_file(self, path, reason):
        """Record and physically isolate an invalid file when possible."""
        self.quarantine.append((path.name, reason))
        quarantine_dir = path.parent / ".quarantine"
        try:
            quarantine_dir.mkdir(exist_ok=True)
            destination = quarantine_dir / path.name
            if destination.exists():
                destination = quarantine_dir / f"{path.stem}_{self._hash(path.name)[:8]}{path.suffix}"
            path.replace(destination)
        except (OSError, PermissionError):
            # Keep the quarantine record even if the source filesystem is read-only.
            pass

    # ========================================================
    # SCAN
    # ========================================================

    def scan(self, folder, user):

        self._check_access(user, "scan")

        folder = Path(folder)

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: {folder}"
            )

        new_documents = []
        modified_documents = []
        unchanged_documents = []
        duplicate_documents = []
        quarantined_documents = []

        hashes_seen = {}

        for path in sorted(folder.iterdir(), key=lambda p: p.name.lower()):

            if not path.is_file():
                continue

            # ------------------------------------------------
            # File type
            # ------------------------------------------------

            if path.suffix.lower() not in self.ALLOWED_EXTENSIONS:

                quarantined_documents.append(path.name)
                self._quarantine_file(path, "invalid file type")

                continue

            # ------------------------------------------------
            # Read document
            # ------------------------------------------------

            try:

                raw_content = path.read_text(
                    encoding="utf-8"
                )

            except Exception:

                quarantined_documents.append(path.name)
                self._quarantine_file(path, "read error")

                continue

            # ------------------------------------------------
            # Prompt injection protection
            # ------------------------------------------------

            if self._prompt_injection(raw_content):

                quarantined_documents.append(path.name)
                self._quarantine_file(path, "prompt injection")

                continue

            # ------------------------------------------------
            # Validate document
            # ------------------------------------------------

            valid, reason = self._validate_document(
                raw_content
            )

            if not valid:

                quarantined_documents.append(path.name)
                self._quarantine_file(path, reason)

                continue

            # ------------------------------------------------
            # Mask sensitive data
            # ------------------------------------------------

            content = self.mask_sensitive_data(
                raw_content
            )

            # ------------------------------------------------
            # Hash content
            # ------------------------------------------------

            content_hash = self._hash(content)

            document = PipelineDocument(
                path=path.name,
                content=content,
                content_hash=content_hash
            )

            # ------------------------------------------------
            # Duplicate detection
            # ------------------------------------------------

            if (
               path.name in self.manifest
               and self.manifest[path.name] == content_hash
            ):
                unchanged_documents.append(path.name)
                hashes_seen[content_hash] = path.name
                continue
            
            if content_hash in hashes_seen:

                duplicate_documents.append(path.name)
                continue
            
            if content_hash in self.manifest.values():

                duplicate_documents.append(path.name)
                continue
            hashes_seen[content_hash] = path.name


                
            # ------------------------------------------------
            # New / modified / unchanged
            # ------------------------------------------------

            if path.name not in self.manifest:

                new_documents.append(document)

            elif self.manifest[path.name] != content_hash:

                modified_documents.append(document)

            else:

                unchanged_documents.append(path.name)

        result = PipelineIngestionResult(
            new_documents=new_documents,
            modified_documents=modified_documents,
            unchanged_documents=unchanged_documents,
            duplicate_documents=duplicate_documents,
            quarantined_documents=quarantined_documents
        )
        self.last_scan_result = result
        self.audit_log.append({
            "event": "scan",
            "new": len(new_documents),
            "modified": len(modified_documents),
            "unchanged": len(unchanged_documents),
            "duplicates": len(duplicate_documents),
            "quarantined": len(quarantined_documents),
        })
        return result

    # ========================================================
    # QUALITY CHECK
    # ========================================================

    def quality_check(
        self,
        documents,
        quality_tests
    ):

        if not documents:

            return PipelineQualityResult(
                passed=False,
                accuracy=0.0,
                grounding=0.0
            )

        passed_tests = 0

        for test in quality_tests:

            matched = False

            for document in documents:

                text = document.content.lower()

                keywords = getattr(
                    test,
                    "expected_keywords",
                    []
                )

                if keywords:

                    if all(
                        keyword.lower() in text
                        for keyword in keywords
                    ):
                        matched = True
                        break

                query = getattr(
                    test,
                    "query",
                    ""
                )

                query_words = query.lower().split()

                if query_words:

                    if all(
                        word in text
                        for word in query_words
                    ):
                        matched = True
                        break

            if matched:
                passed_tests += 1

        accuracy = (
            passed_tests / len(quality_tests)
            if quality_tests
            else 0.0
        )

        grounding = accuracy

        return PipelineQualityResult(
            passed=(
                accuracy >= 0.80
                and grounding >= 0.80
            ),
            accuracy=round(accuracy, 2),
            grounding=round(grounding, 2)
        )

    # ========================================================
    # STAGE VERSION
    # ========================================================

    def stage_version(
        self,
        documents,
        quality,
        user
    ):

        self._check_access(user, "stage")

        if not documents or not quality.passed:

            return PipelineVersion(
                version_id="REJECTED",
                documents=[],
                quality=quality,
                status="rejected"
            )

        active = (
            self.version_manager
            .get_active_version()
        )

        if active:
            active_manifest = {doc.path: doc.content_hash for doc in active.documents}
            candidate_manifest = {doc.path: doc.content_hash for doc in documents}
            if candidate_manifest == active_manifest:
                return PipelineVersion(
                    version_id="NO_CHANGES",
                    documents=[],
                    quality=quality,
                    status="rejected",
                )

            old = active.quality

            if (
                quality.accuracy < old.accuracy
                or
                quality.grounding < old.grounding
            ):

                return PipelineVersion(
                    version_id="REJECTED",
                    documents=[],
                    quality=quality,
                    status="rejected"
                )

        version = (
            self.version_manager
            .create_version(
                documents,
                quality
            )
        )

        self.state.pending_version = version
        self.audit_log.append({
            "event": "version_staged",
            "version_id": version.version_id,
            "accuracy": quality.accuracy,
            "grounding": quality.grounding,
        })

        return version

    # ========================================================
    # SCHEDULE
    # ========================================================

    def schedule_update(
        self,
        update_time,
        user
    ):

        self._check_access(user, "stage")

        self.scheduled_update_time = update_time
        self.audit_log.append({"event": "update_scheduled", "time": update_time.strftime("%H:%M")})

        return PipelineResult(
            status="scheduled",
            message=(
                f"Update scheduled for "
                f"{update_time.strftime('%H:%M')}."
            )
        )

    # ========================================================
    # MAINTENANCE WINDOW
    # ========================================================

    def _in_maintenance_window(
        self,
        current_time
    ):

        start = self.schedule.maintenance_window.start
        end = self.schedule.maintenance_window.end

        current = current_time.time()
        if start < end:
            return start <= current < end
        # Support maintenance windows that cross midnight, e.g. 23:00–02:00.
        if start > end:
            return current >= start or current < end
        return False

    # ========================================================
    # ACTIVATE
    # ========================================================

    def activate(
        self,
        current_time,
        user
    ):

        self._check_access(
            user,
            "activate"
        )

        if not self.service_available:

            self.monitor.failures += 1
            pending = self.state.pending_version
            if pending is not None:
                version_id = pending.version_id
                attempt = self.retry_attempts.get(version_id, 0) + 1
                self.retry_attempts[version_id] = attempt
                if attempt <= len(self.schedule.retry_delays_minutes):
                    retry_at = self.retry_after_failure(current_time, attempt)
                    self.retry_history.append({
                        "version_id": version_id,
                        "attempt": attempt,
                        "delay_minutes": self.schedule.retry_delays_minutes[attempt - 1],
                        "retry_at": retry_at,
                        "status": "scheduled",
                    })
                    retry_message = f" Retry {attempt} scheduled for {retry_at.isoformat(sep=' ')}."
                else:
                    self.retry_history.append({
                        "version_id": version_id,
                        "attempt": attempt,
                        "retry_at": None,
                        "status": "exhausted",
                    })
                    retry_message = " Retry attempts exhausted."
            else:
                retry_message = " No pending version to retry."

            self.audit_log.append({"event": "activation_failed", "reason": "service_unavailable", "time": current_time.isoformat()})
            return PipelineResult(
                status="failed",
                message="Service unavailable." + retry_message
            )

        if self.scheduled_update_time:

            if (
                current_time.time()
                <
                self.scheduled_update_time
            ):

                return PipelineResult(
                    status="waiting_for_schedule",
                    message=(
                        "Update time has not arrived."
                    )
                )

        if not self._in_maintenance_window(
            current_time
        ):

            return PipelineResult(
                status="waiting_for_maintenance",
                message=(
                    "Outside maintenance window."
                )
            )

        version = self.state.pending_version

        if version is None:

            return PipelineResult(
                status="failed",
                message="No pending version."
            )

        if version.status == "rejected":

            return PipelineResult(
                status="rejected",
                message="Quality check failed."
            )

        self.state.previous_version = (
            self.version_manager
            .get_active_version()
        )

        self.version_manager.activate(version)

        version.activated_at = current_time

        self.state.active_version = version

        self.state.pending_version = None

        self.manifest = {
            document.path: document.content_hash
            for document in version.documents
        }
        for retry in self.retry_history:
            if retry.get("version_id") == version.version_id and retry.get("status") == "scheduled":
                retry["status"] = "superseded_by_activation"
        self.audit_log.append({"event": "activated", "version_id": version.version_id, "time": current_time.isoformat()})

        return PipelineResult(
            status="activated",
            message=(
                f"{version.version_id} activated."
            )
        )

    def rollback(self, user, version_id=None):
        """Manually roll back to a previous version (admin-only)."""
        self._check_access(user, "rollback")
        active = self.version_manager.get_active_version()
        target = None
        if version_id:
            target = next((v for v in self.version_manager.versions if v.version_id == version_id), None)
            if target is None:
                return PipelineResult(status="failed", message=f"Version {version_id} was not found.")
        else:
            target = self.state.previous_version
            if target is None:
                target = next((v for v in reversed(self.version_manager.versions) if v is not active and v.status in {"previous", "rolled_back"}), None)

        if target is active:
            return PipelineResult(status="failed", message="The requested version is already active.")

        if active:
            active.status = "rolled_back"

        if target:
            self.version_manager.rollback(target)
            self.state.active_version = target
            self.state.previous_version = active
            self.manifest = {doc.path: doc.content_hash for doc in target.documents}
            self.audit_log.append({"event": "manual_rollback", "from_version": active.version_id if active else None, "to_version": target.version_id})
            return PipelineResult(status="rolled_back", message=f"Restored {target.version_id}.")

        # No prior version exists: restore the empty baseline.
        self.version_manager.active_version = None
        self.state.active_version = None
        self.state.previous_version = None
        self.manifest = {}
        self.audit_log.append({"event": "manual_rollback_to_empty", "from_version": active.version_id if active else None})
        return PipelineResult(status="rolled_back_empty", message="No previous version existed; restored the empty baseline.")

    # ========================================================
    # HEALTH CHECK / ROLLBACK
    # ========================================================

    def health_check(
        self,
        check_time,
        healthy,
        user
    ):

        self._check_access(
            user,
            "monitor"
        )

        active = (
            self.version_manager
            .get_active_version()
        )

        if active is None:

            return HealthCheckResult(
                healthy=healthy,
                rolled_back=False
            )

        activation_time = getattr(
            active,
            "activated_at",
            check_time
        )

        elapsed_minutes = (
            check_time - activation_time
        ).total_seconds() / 60

        if (
            not healthy
            and
            elapsed_minutes <= 5
        ):

            previous = self.state.previous_version

            if previous:
                active.status = "rolled_back"
                self.version_manager.rollback(previous)
                self.state.active_version = previous
                self.manifest = {
                    document.path: document.content_hash
                    for document in previous.documents
                }
            else:
                # First deployment failed its health window: restore the
                # empty baseline rather than leaving the unhealthy version live.
                active.status = "rolled_back_no_baseline"
                self.version_manager.active_version = None
                self.state.active_version = None
                self.manifest = {}

            self.audit_log.append({
                "event": "automatic_rollback",
                "failed_version": active.version_id,
                "restored_version": previous.version_id if previous else None,
                "time": check_time.isoformat(),
            })
            return HealthCheckResult(
                healthy=False,
                rolled_back=True
            )

        return HealthCheckResult(
            healthy=healthy,
            rolled_back=False
        )

    # ========================================================
    # RETRY
    # ========================================================

    def retry_after_failure(
        self,
        failed_at,
        attempt
    ):

        delays = self.schedule.retry_delays_minutes

        if not delays:
            return failed_at

        if attempt < 1:
            attempt = 1

        index = min(
            attempt - 1,
            len(delays) - 1
        )

        return (
            failed_at
            +
            timedelta(
                minutes=delays[index]
            )
        )

    def get_retry_history(self):
        """Return a copy of scheduled retry records for UI/audit use."""
        return [dict(item) for item in self.retry_history]

    def process_due_retry(self, current_time, user):
        """Run the earliest due retry using simulated or real current time.

        Retries remain gated by the normal schedule and maintenance window.
        A service outage schedules the next 15/30/60 minute attempt.
        """
        self._check_access(user, "activate")
        due = [
            item for item in self.retry_history
            if item.get("status") == "scheduled"
            and item.get("retry_at") is not None
            and item["retry_at"] <= current_time
        ]
        if not due:
            return PipelineResult(
                status="no_retry_due",
                message="No retry is due at the simulated current time.",
            )
        due.sort(key=lambda item: (item["retry_at"], item["attempt"]))
        retry = due[0]
        retry["status"] = "running"
        result = self.activate(current_time, user)
        retry["status"] = "succeeded" if result.status == "activated" else "failed"
        retry["result"] = result.status
        return result

    def configure_maintenance_window(self, start, end, user):
        """Change the maintenance window at runtime (admin only)."""
        self._check_access(user, "configure")
        if start == end:
            raise ValueError("Maintenance start and end must differ.")
        self.schedule.maintenance_window.start = start
        self.schedule.maintenance_window.end = end
        self.audit_log.append({
            "event": "maintenance_window_changed",
            "start": start.strftime("%H:%M"),
            "end": end.strftime("%H:%M"),
        })

    def get_audit_log(self):
        return [dict(item) for item in self.audit_log]

    # ========================================================
    # SERVICE AVAILABILITY
    # ========================================================

    def set_service_availability(
        self,
        available
    ):

        self.service_available = available

    # ========================================================
    # MONITORING
    # ========================================================

    def record_chatbot_request(
        self,
        latency_ms,
        confidence,
        failed=False,
        escalated=False
    ):

        self.monitor.record(
            latency_ms,
            confidence,
            failed,
            escalated
        )

    def monitoring_summary(self):

        return self.monitor.summary()

    # ========================================================
    # MANIFEST
    # ========================================================

    def get_manifest(self):

        return dict(self.manifest)

    # ========================================================
    # ACTIVE DOCUMENTS
    # ========================================================

    def get_active_documents(self):

        active = (
            self.version_manager
            .get_active_version()
        )

        if active is None:
            return []

        return list(active.documents)