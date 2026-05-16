from __future__ import annotations

import json
import logging
from typing import Dict, Any, Iterable

# Prefer httpx for streaming requests (supports sync and async). If httpx
# is not available fall back to the stdlib urllib implementation used earlier.
try:
    import httpx  # type: ignore
    _HAS_HTTPX = True
except Exception:
    httpx = None  # type: ignore
    _HAS_HTTPX = False

from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlparse


def _stream_chat_once(
    base_url: str, payload: Dict[str, Any], timeout_s: float
) -> Iterable[Dict[str, Any]]:
    """Yield parsed JSON objects from an Ollama streaming endpoint."""
    data = json.dumps(payload).encode("utf-8")
    # Allow the caller to provide either a base URL (e.g. 'http://host:port')
    # or a full endpoint (e.g. 'http://host:port/api/chat' or
    # 'http://host:port/v1/chat'). If the provided base_url already contains
    # '/api' or ends with 'chat' assume it's a full endpoint.
    if "/api/" in (base_url or "") or (base_url or "").rstrip("/").endswith("chat"):
        endpoint = base_url
    else:
        endpoint = f"{(base_url or "").rstrip('/')}/api/chat"

    # Log the endpoint being called to aid debugging when the server returns
    # HTTP errors (404/403) so the user can confirm the correct URL.
    logging.getLogger(__name__).debug("Ollama endpoint: %s", endpoint)

    # If httpx is available we prefer it for streaming support. If it fails
    # with a 404 we fall back to the urllib implementation below.
    if _HAS_HTTPX:
        try:
            with httpx.Client(timeout=timeout_s) as client:
                with client.stream("POST", endpoint, json=payload) as response:
                    response.raise_for_status()
                    for chunk in response.iter_text():
                        if not chunk:
                            continue
                        for line in chunk.splitlines():
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                parsed = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            if isinstance(parsed, dict):
                                yield parsed
                    return
        except Exception as err:
            # If it's an HTTPStatusError with 404, fall through to urllib
            try:
                code = err.response.status_code  # type: ignore[attr-defined]
            except Exception:
                code = None
            if code != 404:
                raise
            logging.getLogger(__name__).debug("httpx returned 404, falling back to urllib")

    req = Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    # Try the computed endpoint and, on 404, attempt a couple of reasonable
    # alternatives derived from the host (e.g., stripping a '/v1' segment).
    endpoints_tried = [endpoint]

    def _open(u: str):
        r = Request(u, data=data, headers={"Content-Type": "application/json"}, method="POST")
        return urlopen(r, timeout=timeout_s)

    try:
        with _open(endpoint) as response:
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
            return
    except HTTPError as err:
        # If 404, try alternatives based on scheme+netloc
        if err.code == 404:
            parsed = urlparse(base_url or "")
            if parsed.scheme and parsed.netloc:
                root = f"{parsed.scheme}://{parsed.netloc}"
                alt_api = f"{root}/api/chat"
                alt_v1 = f"{root}/v1/chat"
                for alt in (alt_api, alt_v1):
                    if alt == endpoint:
                        continue
                    logging.getLogger(__name__).debug("Retrying Ollama endpoint: %s", alt)
                    endpoints_tried.append(alt)
                    try:
                        with _open(alt) as response:
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
                            return
                    except HTTPError:
                        continue
        # If we fall through, re-raise so upstream logs the original error
        raise
