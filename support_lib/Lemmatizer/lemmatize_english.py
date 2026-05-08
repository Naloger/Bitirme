# -*- coding: utf-8 -*-
from __future__ import annotations

import re

import spacy
from nltk.stem import WordNetLemmatizer

from .normalize_output import normalize_lemmatized_output


ENGLISH_MODEL_NAME = "en_core_web_sm"

try:
    _spacy_en = spacy.load(ENGLISH_MODEL_NAME)
except Exception:
    _spacy_en = None


def lemmatize_english_text(text: str) -> list[str]:
    """Lemmatize English text and return sentence-level lines."""
    parts = re.split(r"[\n.!?;:,—\-\"']+", text)
    out: list[str] = []

    for part in parts:
        sentence = part.strip().rstrip(".,!?;:'\"—-")
        if not sentence:
            continue

        if _spacy_en is not None:
            doc = _spacy_en(sentence)
            words = [t.lemma_.lower() for t in doc if t.text.strip()]
        else:
            # Lightweight fallback when spaCy model is unavailable.
            words = []
            fallback = WordNetLemmatizer()
            for w in re.findall(r"\w+", sentence, flags=re.UNICODE):
                normalized = w.lower()
                lemma_v = fallback.lemmatize(normalized, pos="v")
                words.append(
                    lemma_v
                    if lemma_v != normalized
                    else fallback.lemmatize(normalized, pos="n")
                )

        if words:
            out.append(" ".join(words))

    # Apply normalization to remove artifacts and single-char tokens
    normalized_out: list[str] = []
    for line in out:
        tokens = line.split()
        cleaned_tokens = normalize_lemmatized_output(tokens)
        if cleaned_tokens:
            normalized_out.append(" ".join(cleaned_tokens))

    return normalized_out
