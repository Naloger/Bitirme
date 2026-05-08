# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any

from langdetect import detect_langs
from langdetect.lang_detect_exception import LangDetectException

try:
    import stanza
    from stanza.pipeline.core import DownloadMethod
except Exception:
    stanza = None
    DownloadMethod = None


_stanza_langid_pipeline: Any | None = None
_stanza_langid_init_attempted = False


def _get_stanza_langid_pipeline() -> Any | None:
    """Create and cache a binary (en/tr) stanza language-id pipeline."""
    global _stanza_langid_pipeline, _stanza_langid_init_attempted
    if _stanza_langid_init_attempted:
        return _stanza_langid_pipeline

    _stanza_langid_init_attempted = True
    if stanza is None or DownloadMethod is None:
        return None

    try:
        _stanza_langid_pipeline = stanza.MultilingualPipeline(
            lang_id_config={"langid_lang_subset": ["en", "tr"]},
            processors="tokenize",
            restrict=True,
            use_gpu=False,
            download_method=DownloadMethod.REUSE_RESOURCES,
        )
    except Exception:
        _stanza_langid_pipeline = None

    return _stanza_langid_pipeline


def detect_text_language(text: str) -> str:
    """Return 'tr' or 'en' using model-based ensemble detection."""
    cleaned = text.strip()
    if not cleaned:
        return "en"

    # Aggregate probabilities on sentence-like segments for better stability.
    segments = [s.strip() for s in re.split(r"[\n.!?;:]+", cleaned) if s.strip()]
    if not segments:
        segments = [cleaned]

    scores = {"en": 0.0, "tr": 0.0}

    # Primary signal: stanza language-id model constrained to en/tr.
    stanza_langid = _get_stanza_langid_pipeline()
    if stanza_langid is not None:
        for segment in segments:
            alpha_count = len(
                re.findall(
                    r"[A-Za-z\u00C0-\u024F\u1E00-\u1EFF\u0370-\u03FF\u0400-\u04FF]",
                    segment,
                )
            )
            if alpha_count < 2:
                continue

            weight = max(1.0, alpha_count / 8.0)
            try:
                doc = stanza_langid(segment)
                lang = str(getattr(doc, "lang", "")).lower()
                if lang.startswith("tr"):
                    scores["tr"] += weight
                elif lang.startswith("en"):
                    scores["en"] += weight
            except Exception:
                continue

    # Secondary signal: probability-based langdetect.
    for segment in segments:
        alpha_count = len(
            re.findall(
                r"[A-Za-z\u00C0-\u024F\u1E00-\u1EFF\u0370-\u03FF\u0400-\u04FF]", segment
            )
        )
        if alpha_count < 3:
            continue

        weight = max(1.0, alpha_count / 8.0)
        try:
            for candidate in detect_langs(segment):
                lang = (
                    "tr"
                    if candidate.lang.startswith("tr")
                    else "en"
                    if candidate.lang.startswith("en")
                    else ""
                )
                if lang:
                    scores[lang] += float(candidate.prob) * weight * 0.75
        except LangDetectException:
            continue

    if scores["tr"] == 0.0 and scores["en"] == 0.0:
        return "en"

    return "tr" if scores["tr"] > scores["en"] else "en"
