# -*- coding: utf-8 -*-
from __future__ import annotations

import re

from .turkish_chars import TURKISH_DIACRITICS_MAP, restore_turkish_diacritics


MIN_WORD_LENGTH = 2
"""Minimum character length for a lemmatized token to be kept."""

STOPWORD_PATTERNS = {
    "^[aeiou]$",  # Single vowels
    "^m$",  # Turkish suffix artifact
    "^be$",  # English auxiliary remnant
    "^a$",  # Article/indefinite marker
}
"""Regex patterns for tokens to exclude."""

_COMPILED_STOPWORDS = [re.compile(p) for p in STOPWORD_PATTERNS]


def _should_filter(token: str) -> bool:
    """Check if a token should be excluded from lemmatization output."""
    return any(pattern.match(token.lower()) for pattern in _COMPILED_STOPWORDS)


def normalize_lemmatized_output(tokens: list[str]) -> list[str]:
    """Filter and normalize lemmatized tokens for cleaner output.

    Args:
        tokens: List of lemmatized word tokens

    Returns:
        Filtered list of normalized tokens with Turkish diacritics restored
    """
    normalized: list[str] = []

    for token in tokens:
        cleaned = token.strip()

        if not cleaned:
            continue

        # Skip punctuation-only tokens
        if not re.search(r"[a-zA-Z]", cleaned):
            continue

        # Skip if token is too short
        if len(cleaned) < MIN_WORD_LENGTH:
            continue

        # Skip stopword patterns
        if _should_filter(cleaned):
            continue

        # Restore Turkish diacritics for known Turkish words
        if cleaned.lower() in TURKISH_DIACRITICS_MAP:
            cleaned = TURKISH_DIACRITICS_MAP[cleaned.lower()]

        normalized.append(cleaned)

    return normalized


def normalize_lemmatized_text(text: str) -> str:
    """Normalize a space-separated string of lemmatized words.

    Args:
        text: Space-separated lemmatized words

    Returns:
        Cleaned and normalized text with Turkish diacritics restored
    """
    tokens = text.split()
    normalized = normalize_lemmatized_output(tokens)
    result = " ".join(normalized)
    # Restore Turkish diacritics if any Turkish words are present
    return restore_turkish_diacritics(result)
