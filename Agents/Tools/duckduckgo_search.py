from __future__ import annotations

from typing import List, Dict

import requests


def duckduckgo_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Search DuckDuckGo Instant Answer API and return a list of result dicts.

    This uses the DuckDuckGo Instant Answer API which provides summaries and
    related topics. It does not return the same set as a full search engine
    results page but is fast and doesn't require an API key.

    Example return element: {"title": ..., "snippet": ..., "url": ...}
    """
    if not query:
        return []

    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}

    if requests is None:
        raise RuntimeError("requests package is required for duckduckgo_search")

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results: List[Dict[str, str]] = []

    # If an abstract exists, include it
    abstract = data.get("AbstractText")
    abstract_url = data.get("AbstractURL")
    if abstract:
        results.append(
            {
                "title": data.get("Heading") or query,
                "snippet": abstract,
                "url": abstract_url or "",
            }
        )

    # RelatedTopics can contain topics or nested topics
    related = data.get("RelatedTopics", [])
    for item in related:
        if len(results) >= max_results:
            break
        if "Text" in item:
            results.append(
                {
                    "title": item.get("Text"),
                    "snippet": item.get("Result") or "",
                    "url": item.get("FirstURL") or "",
                }
            )
        else:
            # sometimes a group with 'Topics'
            for sub in item.get("Topics", []):
                if len(results) >= max_results:
                    break
                results.append(
                    {
                        "title": sub.get("Text"),
                        "snippet": sub.get("Result") or "",
                        "url": sub.get("FirstURL") or "",
                    }
                )

    # Truncate to requested count
    return results[:max_results]
