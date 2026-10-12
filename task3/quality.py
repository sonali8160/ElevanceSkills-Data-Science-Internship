# task3/quality.py


def quality_score(documents):
    """Calculate a simple quality score."""

    if not documents:
        return 0.0

    valid = 0

    for doc in documents.values():
        content = doc["content"].strip()

        if len(content) >= 20:
            valid += 1

    return round(valid / len(documents), 2)


def check_quality(old_documents, new_documents):
    """Reject updates that reduce quality."""

    old_score = quality_score(old_documents)
    new_score = quality_score(new_documents)

    return {
        "old_score": old_score,
        "new_score": new_score,
        "approved": new_score >= old_score
    }


def grounding_check(documents):
    """Basic grounding check: every document must contain content."""

    return all(
        bool(doc["content"].strip())
        for doc in documents.values()
    )