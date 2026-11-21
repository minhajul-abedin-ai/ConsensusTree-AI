"""Deterministic, offline agreement diagnostics for independent reviewer labels.

These statistics describe votes, not whether any reviewer is correct.
"""
from collections import Counter
from typing import Iterable, Optional


def summarize_votes(votes: Iterable[Optional[str]]) -> dict:
    """Summarize votes; None is an abstention, labels must be nonblank strings.

    Raises ValueError for empty input or invalid labels. Ties have no winner.
    """
    items = list(votes)
    if not items:
        raise ValueError("at least one reviewer vote is required")
    for vote in items:
        if vote is not None and (not isinstance(vote, str) or not vote.strip()):
            raise ValueError("votes must be nonblank strings or None")
    counts = Counter(vote for vote in items if vote is not None)
    eligible = sum(counts.values())
    top = max(counts.values(), default=0)
    leaders = sorted(label for label, count in counts.items() if count == top)
    winner = leaders[0] if len(leaders) == 1 else None
    return {
        "reviewers": len(items),
        "responded": eligible,
        "abstained": len(items) - eligible,
        "counts": dict(sorted(counts.items())),
        "winner": winner,
        "tie": len(leaders) > 1,
        "unanimous_among_responses": eligible > 0 and len(counts) == 1,
        "winner_share_of_all": (top / len(items)) if winner is not None else None,
    }
