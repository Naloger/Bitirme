from __future__ import annotations

import time
from typing import List, Dict

from Agents.Tools.crawl_page import crawl_page


def crawl_urls(
    urls: List[str], delay: float = 0.5, max_chars: int = 10000
) -> List[Dict[str, str]]:
    """Crawl a list of URLs sequentially with an optional delay between requests."""
    out = []
    for u in urls:
        out.append(crawl_page(u, max_chars=max_chars))
        time.sleep(delay)
    return out
