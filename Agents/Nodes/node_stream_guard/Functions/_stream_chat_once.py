from __future__ import annotations

import json
from typing import Dict, Any, Iterable
from urllib.request import Request, urlopen


def _stream_chat_once(
    base_url: str, payload: Dict[str, Any], timeout_s: int
) -> Iterable[Dict[str, Any]]:
    """Yield parsed JSON objects from an Ollama streaming endpoint."""
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(req, timeout=timeout_s) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                yield parsed
