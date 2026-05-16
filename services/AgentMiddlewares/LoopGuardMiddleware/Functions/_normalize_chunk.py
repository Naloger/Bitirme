from __future__ import annotations

import re


def _normalize_chunk(text: str) -> str:
    """Normalize whitespace and case for stable loop comparison."""
    return re.sub(r"\s+", " ", text.strip().lower())
