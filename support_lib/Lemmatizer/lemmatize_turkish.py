# -*- coding: utf-8 -*-
from __future__ import annotations

import re

import stanza

from .normalize_output import normalize_lemmatized_output


TURKISH_MODEL_NAME = "stanza-tr"

try:
    _stanza_tr = stanza.Pipeline(
        lang="tr",
        processors="tokenize,mwt,pos,lemma",
        use_gpu=False,
        verbose=False,
    )
except Exception:
    _stanza_tr = None


def lemmatize_turkish_text(text: str) -> list[str]:
    """Lemmatize Turkish text and return sentence-level lines."""
    parts = re.split(r"[\n.!?;:,—\-\"']+", text)
    out: list[str] = []

    for part in parts:
        sentence = part.strip().rstrip(".,!?;:'\"—-")
        if not sentence:
            continue

        words: list[str] = []
        if _stanza_tr is not None:
            try:
                doc = _stanza_tr(sentence)
                for sent in getattr(doc, "sentences", []):
                    for word in getattr(sent, "words", []):
                        lemma = str(
                            getattr(word, "lemma", getattr(word, "text", ""))
                        ).lower()
                        lemma = lemma.strip().rstrip(".,!?;:'\"—-")
                        if lemma:
                            words.append(lemma)
            except RuntimeError:
                pass

        if not words:
            words = [w.lower() for w in re.findall(r"\w+", sentence, flags=re.UNICODE)]

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
