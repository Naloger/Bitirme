# -*- coding: utf-8 -*-
from __future__ import annotations

import re

from langdetect import LangDetectException, detect


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def detect_text_language(text: str) -> str:
    """Detect the language of `text` using langdetect only.

    The detector returns the language code reported by langdetect when possible.
    If detection fails, it falls back to 'gibberish' as a safe default.

    This stays lightweight and lets future multilingual lemmatizers plug in by
    simply adding their language code to the lemmatizer map.
    """
    cleaned = _normalize(text)
    if not cleaned:
        raise RuntimeError("empty text provided for language detection")

    try:
        return detect(cleaned).lower()
    except LangDetectException:
        if any(c.isalpha() for c in cleaned):
            return "en"
        return "gibberish"

