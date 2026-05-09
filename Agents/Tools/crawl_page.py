from __future__ import annotations

import re
from typing import Dict

import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


def crawl_page(url: str, max_chars: int = 10000, timeout: int = 10) -> Dict[str, str]:
    """Fetch a single page and return a small dict with title and text snippet.

    If BeautifulSoup is available, uses it to extract the title and visible text.
    Otherwise tries a simple HTML-to-text fallback.
    """
    # Note: requests is already imported at top level,
    # checking 'if requests is None' is only needed if you lazy-import.

    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        return {"url": url, "title": "", "text": f"<error fetching page: {e}>"}

    title = ""
    text = ""
    use_fallback = BeautifulSoup is None

    # Try BeautifulSoup if available
    if not use_fallback:
        try:
            soup = BeautifulSoup(html, "html.parser")
            t = soup.title
            title = str(t.string).strip() if t and t.string is not None else ""

            # Extract visible text
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()

            visible = soup.get_text(separator=" ")
            text = re.sub(r"\s+", " ", visible).strip()
        except Exception:
            use_fallback = True

    if use_fallback:
        # crude fallback: strip tags
        title_match = re.search(
            r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL
        )
        title = title_match.group(1).strip() if title_match else ""
        # Remove tags
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()

    if len(text) > max_chars:
        text = text[:max_chars] + "..."

    return {"url": url, "title": title, "text": text}
