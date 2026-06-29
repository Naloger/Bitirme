from __future__ import annotations

from collections import deque, Counter


def _detect_loop(window: deque[str], repetition_limit: int) -> bool:
    """Determine whether the recent chunk window exhibits repetitive behavior."""
    if len(window) < repetition_limit:
        return False

    recent = list(window)[-repetition_limit:]
    if recent[0] and len(set(recent)) == 1:
        return True

    text = " ".join(window)
    tokens = text.split()
    if len(tokens) < 12:
        return False

    n = 5
    ngrams = [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]
    if not ngrams:
        return False

    most_common_ngram, count = Counter(ngrams).most_common(1)[0]
    threshold = max(3, repetition_limit - 1)
    return count >= threshold
