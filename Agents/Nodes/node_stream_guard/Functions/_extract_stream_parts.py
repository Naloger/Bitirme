from __future__ import annotations

from typing import Dict, Any, Tuple


def _extract_stream_parts(chunk: Dict[str, Any]) -> Tuple[str, str, bool]:
    """Extract content, thinking, and completion status from an Ollama stream chunk."""
    if not isinstance(chunk, dict):
        return "", "", False

    message = chunk.get("message")
    content = ""
    thinking = ""

    if isinstance(message, dict):
        content = str(message.get("content", "") or "")
        thinking = str(message.get("thinking", "") or "") or str(
            message.get("thinking_output", "") or ""
        )

    if not content:
        content = str(chunk.get("response", "") or "")
    if not thinking:
        thinking = str(chunk.get("thinking", "") or "")

    done = bool(chunk.get("done", False))
    return content, thinking, done
