from .models import MessageAnalysis


# ============================================================
# TONE SELECTION
# ============================================================

def get_recommended_tone(
    analysis: MessageAnalysis,
) -> str:
    """
    Select an appropriate response tone.

    IMPORTANT:
    Tone changes only the communication style.
    It must never change business rules, prices,
    refund limits, SLAs, eligibility, or policies.
    """

    # Highest priority: sarcasm
    if analysis.sarcastic:
        return "calm_and_professional"

    # High-risk / urgent issues
    if analysis.urgent:
        return "direct_and_reassuring"

    # Frustration
    if analysis.frustrated:
        return "calming_and_empathetic"

    # Sentiment
    if analysis.sentiment == "positive":
        return "friendly"

    if analysis.sentiment == "negative":
        return "empathetic"

    return "professional"


# ============================================================
# TONE INSTRUCTION
# ============================================================

def get_tone_instruction(
    analysis: MessageAnalysis,
) -> str:

    tone = get_recommended_tone(analysis)

    instructions = {

        "friendly": (
            "Use a warm, friendly and appreciative tone. "
            "Acknowledge the customer's positive experience."
        ),

        "professional": (
            "Use a clear, professional and informative tone. "
            "Answer directly and avoid unnecessary emotional language."
        ),

        "empathetic": (
            "Use an empathetic and respectful tone. "
            "Acknowledge the customer's concern and provide "
            "clear next steps."
        ),

        "calming_and_empathetic": (
            "Use a calm, patient and empathetic tone. "
            "Acknowledge the frustration, avoid defensive language, "
            "and clearly explain the next available action."
        ),

        "direct_and_reassuring": (
            "Use a direct, concise and reassuring tone. "
            "Prioritize the immediate issue and explain the "
            "next action clearly."
        ),

        "calm_and_professional": (
            "Use a calm, neutral and professional tone. "
            "Do not mirror sarcasm or hostility. "
            "Focus on facts and the appropriate next step."
        ),
    }

    return instructions[tone]


# ============================================================
# RESPONSE TONE ADJUSTMENT
# ============================================================

def adjust_response_tone(
    response: str,
    analysis: MessageAnalysis,
) -> str:
    """
    Adds tone guidance to a response without changing
    the underlying business information.

    The actual business answer remains unchanged.
    """

    if not isinstance(response, str):
        raise TypeError(
            "response must be a string."
        )

    tone = get_recommended_tone(analysis)

    instruction = get_tone_instruction(analysis)

    return (
        f"[Response Tone: {tone}]\n"
        f"[Tone Guidance: {instruction}]\n\n"
        f"{response}"
    )


# ============================================================
# POLICY PRESERVATION
# ============================================================

def preserve_business_policy(
    response: str,
) -> str:
    """
    Explicitly marks a response as policy-preserving.

    This function does NOT modify business rules.
    """

    return response