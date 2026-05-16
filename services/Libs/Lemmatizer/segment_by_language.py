# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import TypedDict

from .detect_language import detect_text_language


class LanguageSegment(TypedDict):
    language: str
    text: str


def segment_by_language(text: str) -> list[LanguageSegment]:
    """Split text into simple language-marked segments ('en' / 'tr')."""
    raw_parts = [p.strip() for p in re.split(r"([.!?\n]+)", text) if p and p.strip()]
    segments: list[LanguageSegment] = []

    for part in raw_parts:
        if re.fullmatch(r"[.!?\n]+", part):
            if segments:
                segments[-1]["text"] += part
            continue

        lang = detect_text_language(part)
        if segments and segments[-1]["language"] == lang:
            segments[-1]["text"] += " " + part
        else:
            segments.append({"language": lang, "text": part})

    return segments


def mark_text_by_language(text: str) -> list[str]:
    """Return labeled lines like: [en] hello world"""
    return [f"[{seg['language']}] {seg['text']}" for seg in segment_by_language(text)]
