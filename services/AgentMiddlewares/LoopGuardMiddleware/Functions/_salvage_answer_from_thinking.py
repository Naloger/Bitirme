from __future__ import annotations

import re


def _salvage_answer_from_thinking(thinking_text: str) -> str:
    """Attempt to extract a coherent final answer from reasoning traces."""
    if not thinking_text:
        return ""

    draft_matches = re.findall(
        r"\*\s*Draft\s*\d+\s*:\s*([^\n]+)", thinking_text, flags=re.IGNORECASE
    )
    if draft_matches:
        candidate = draft_matches[-1].strip().strip('"')
        if candidate:
            return candidate.rstrip(" .") + "."

    flat = re.sub(r"\s+", " ", thinking_text).strip()
    parts = re.split(r"(?<=[.!?])\s+", flat)
    for part in parts:
        text = part.strip().strip('"')
        if len(text) >= 40 and "thinking process" not in text.lower():
            return text.rstrip(" .") + "."

    return ""
