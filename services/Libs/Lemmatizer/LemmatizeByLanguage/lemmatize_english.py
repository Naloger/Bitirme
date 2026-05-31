# -*- coding: utf-8 -*-
from __future__ import annotations

from functools import lru_cache

import spacy

from services.Libs.Lemmatizer.Models.model_cache import (
    print_model_setup_instructions,
)

ENGLISH_MODEL_NAME = "en_core_web_sm"

_PLURAL_NOUN_TAGS = {"NNS", "NNPS"}

@lru_cache(maxsize=1)
def _load_nlp():
    """Load the spaCy English model used for all lemmatization.

    Models are cached persistently in LEMMATIZER_MODELS_DIR (~/.cache/lemmatizer_models/ by default).
    On first use, models are automatically downloaded to the cache directory.
    """
    try:
        return spacy.load(ENGLISH_MODEL_NAME)
    except (OSError, ValueError) as exc:
        print_model_setup_instructions()
        raise RuntimeError(
            f"Required spaCy model '{ENGLISH_MODEL_NAME}' is not available. "
            f"Run: python -m spacy download {ENGLISH_MODEL_NAME}"
        ) from exc


def _has_blocked_affix(word: str, prefixes: tuple[str, ...], suffixes: tuple[str, ...]) -> bool:
    lowered = word.lower().strip()
    return any(lowered.startswith(prefix.lower()) for prefix in prefixes) or any(
        lowered.endswith(suffix.lower()) for suffix in suffixes
    )


# 1. Lemmatization function
def lemmatize(
    text: str,
    *,
    disallow_plural_nouns: bool = False,
    blocked_prefixes: tuple[str, ...] = (),
    blocked_suffixes: tuple[str, ...] = (),
):
    """Return normalized English lemmas with optional morphological filtering.

    Args:
        text: Input text to normalize.
        disallow_plural_nouns: Skip obvious plural noun forms.
        blocked_prefixes: Reject tokens that start with any of these prefixes.
        blocked_suffixes: Reject tokens that end with any of these suffixes.
    """
    if not text:
        return []

    lemmas: list[str] = []
    nlp = _load_nlp()
    for token in nlp(text):
        if token.is_punct or token.is_space:
            continue

        original = token.text.lower().strip()
        if not original:
            continue

        if disallow_plural_nouns and token.tag_ in _PLURAL_NOUN_TAGS:
            continue

        lemma = token.lemma_.lower().strip()
        if not lemma:
            continue

        if blocked_prefixes or blocked_suffixes:
            if _has_blocked_affix(original, blocked_prefixes, blocked_suffixes):
                continue
            if _has_blocked_affix(lemma, blocked_prefixes, blocked_suffixes):
                continue

        lemmas.append(lemma)

    return lemmas

