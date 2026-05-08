# -*- coding: utf-8 -*-
"""Turkish character normalization and preservation utilities."""
from __future__ import annotations

from .turkish_diacritics_data import load_turkish_diacritics

# Turkish common words that should preserve diacritics
# This is the core mapping that's always included
TURKISH_DIACRITICS_MAP = load_turkish_diacritics()


def restore_turkish_diacritics(text: str) -> str:
    """Restore Turkish diacritics to common Turkish words.

    Args:
        text: Text that may contain Turkish words without diacritics

    Returns:
        Text with Turkish diacritics restored where applicable
    """
    words = text.split()
    restored_words: list[str] = []

    for word in words:
        lower_word = word.lower()
        # Direct mapping lookup for known Turkish words
        if lower_word in TURKISH_DIACRITICS_MAP:
            restored_words.append(TURKISH_DIACRITICS_MAP[lower_word])
        else:
            restored_words.append(word)

    return " ".join(restored_words)


def extend_turkish_diacritics(additional_words: dict) -> None:
    """Extend the Turkish diacritics dictionary with custom words.

    Args:
        additional_words: Dictionary of {word_without_diacritics: word_with_diacritics}

    Example:
        extend_turkish_diacritics({
            'isik': 'ışık',
            'cadir': 'çadır',
        })
    """
    TURKISH_DIACRITICS_MAP.update(additional_words)


def has_turkish_chars(text: str) -> bool:
    """Check if text contains Turkish characters with diacritics."""
    turkish_chars = set('çğıöşüÇĞİÖŞÜ')
    return any(char in text for char in turkish_chars)


def preserve_text_case_pattern(original: str, normalized: str) -> str:
    """Preserve case pattern from original to normalized text.

    If original was uppercase/title case, apply that to normalized.
    """
    if not original:
        return normalized

    if original[0].isupper():
        return normalized[0].upper() + normalized[1:] if len(normalized) > 1 else normalized.upper()

    return normalized

