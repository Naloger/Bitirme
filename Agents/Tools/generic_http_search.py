from __future__ import annotations

from typing import Optional, Union

import requests


def generic_http_search(
    endpoint: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    method: str = "GET",
    timeout: int = 10,
) -> Union[dict, str]:
    """Call a generic HTTP search endpoint and return JSON or text.

    Args:
            endpoint: full URL
            params: query params or body (for POST)
            headers: optional headers
            method: 'GET' or 'POST'
            timeout: seconds

    Returns:
            Parsed JSON if response is JSON, otherwise raw text.
    """
    if requests is None:
        raise RuntimeError("requests package is required for generic_http_search")

    method = method.upper()
    if method == "GET":
        resp = requests.get(endpoint, params=params, headers=headers, timeout=timeout)
    else:
        resp = requests.post(endpoint, json=params, headers=headers, timeout=timeout)

    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "")
    if "application/json" in content_type:
        return resp.json()
    # Prefer text; if the response is bytes, decode to a string safely
    try:
        return resp.text
    except UnicodeError:
        return resp.content.decode("utf-8", errors="replace")
