from datetime import datetime
from typing import List, Optional

from .analyzer import analyze_message
from .escalation import evaluate_escalation
from .models import (
    ConversationMessage,
    EscalationResult,
    MessageAnalysis,
)
from .tone import (
    adjust_response_tone,
    get_tone_instruction,
)


class ConversationManager:

    def __init__(self):

        self.messages: List[
            ConversationMessage
        ] = []

        self.resolved = False

        self.escalation_history: List[
            EscalationResult
        ] = []

    # ========================================================
    # ADD MESSAGE
    # ========================================================

    def add_message(
        self,
        text: str,
        timestamp: datetime,
        role: str = "user",
    ) -> Optional[MessageAnalysis]:

        if role not in {
            "user",
            "assistant",
        }:

            raise ValueError(
                "role must be 'user' or 'assistant'."
            )

        analysis = None

        if role == "user":

            prior_user_messages = [
                message.text
                for message in self.messages
                if message.role == "user"
            ]

            analysis = analyze_message(
                text,
                history=prior_user_messages,
            )

            # New user message means the issue may
            # no longer be resolved.
            self.resolved = False

        message = ConversationMessage(
            text=text,
            timestamp=timestamp,
            role=role,
            analysis=analysis,
        )

        self.messages.append(message)

        return analysis

    # ========================================================
    # GET HISTORY
    # ========================================================

    def get_history(
        self,
    ) -> List[ConversationMessage]:

        return self.messages.copy()

    # ========================================================
    # LATEST ANALYSIS
    # ========================================================

    def latest_analysis(
        self,
    ) -> Optional[MessageAnalysis]:

        for message in reversed(
            self.messages
        ):

            if (
                message.role == "user"
                and message.analysis is not None
            ):

                return message.analysis

        return None

    # ========================================================
    # TONE INSTRUCTION
    # ========================================================

    def get_current_tone_instruction(
        self,
    ) -> str:

        analysis = self.latest_analysis()

        if analysis is None:

            return (
                "Use a professional and helpful tone."
            )

        return get_tone_instruction(
            analysis
        )

    # ========================================================
    # APPLY TONE TO RESPONSE
    # ========================================================

    def adjust_response(
        self,
        response: str,
    ) -> str:

        analysis = self.latest_analysis()

        if analysis is None:
            return response

        return adjust_response_tone(
            response,
            analysis,
        )

    # ========================================================
    # MARK CONVERSATION RESOLVED
    # ========================================================

    def mark_resolved(self):

        self.resolved = True

    # ========================================================
    # CHECK RESOLUTION STATUS
    # ========================================================

    def is_resolved(self) -> bool:

        return self.resolved

    # ========================================================
    # CHECK ESCALATION
    # ========================================================

    def check_escalation(
        self,
        current_time: datetime,
    ) -> EscalationResult:

        result = evaluate_escalation(
            messages=self.messages,
            current_time=current_time,
            resolved=self.resolved,
        )

        if result.required:
            # Polling the same conversation repeatedly should not create
            # duplicate audit entries for the same active escalation.
            signature = (
                result.queue,
                tuple(result.activated_conditions),
                result.conversation_summary,
            )
            already_recorded = any(
                (
                    item.queue,
                    tuple(item.activated_conditions),
                    item.conversation_summary,
                ) == signature
                for item in self.escalation_history
            )

            if not already_recorded:
                self.escalation_history.append(result)

        return result

    # ========================================================
    # ESCALATION HISTORY
    # ========================================================

    def get_escalation_history(
        self,
    ) -> List[EscalationResult]:

        return self.escalation_history.copy()

    # ========================================================
    # CLEAR CONVERSATION
    # ========================================================

    def clear(self):

        self.messages.clear()

        self.escalation_history.clear()

        self.resolved = False