"""Utility helper functions for LangChain-style tools.

Provided utilities:
- get_datetime: returns current date/time (ISO + human-readable)
- duckduckgo_search: use DuckDuckGo Instant Answer API to get summaries
- generic_http_search: simple wrapper to call arbitrary HTTP search endpoints
- crawl_page / crawl_urls: fetch page(s) and return title/snippet/content
- read_file: read a file from disk
- discover_dirs: list directories and files under a path
- write_markdown: write markdown to a file (create parent dirs)

The implementations use only the Python standard library plus `requests` if
available. They are designed to be useful as small utilities inside agents
or LangChain tools.
"""

from __future__ import annotations

import datetime
import os
import re
import time
from typing import Dict, List, Optional, Union
from bs4 import BeautifulSoup  # type: ignore
import requests


def get_datetime(tz: Optional[datetime.tzinfo] = None) -> Dict[str, str]:
	"""Return current date/time in ISO format and a human-friendly string.

	Args:
		tz: optional timezone (datetime.tzinfo). If omitted, uses system local time.

	Returns:
		dict with keys: 'iso', 'human', 'timestamp'
	"""
	now = datetime.datetime.now(tz=tz)
	return {
		"iso": now.isoformat(),
		"human": now.strftime("%Y-%m-%d %H:%M:%S"),
		"timestamp": str(int(now.timestamp())),
	}


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
		results.append({"title": data.get("Heading") or query, "snippet": abstract, "url": abstract_url or ""})

	# RelatedTopics can contain topics or nested topics
	related = data.get("RelatedTopics", [])
	for item in related:
		if len(results) >= max_results:
			break
		if "Text" in item:
			results.append({"title": item.get("Text"), "snippet": item.get("Result") or "", "url": item.get("FirstURL") or ""})
		else:
			# sometimes a group with 'Topics'
			for sub in item.get("Topics", []):
				if len(results) >= max_results:
					break
				results.append({"title": sub.get("Text"), "snippet": sub.get("Result") or "", "url": sub.get("FirstURL") or ""})

	# Truncate to requested count
	return results[:max_results]


def generic_http_search(endpoint: str, params: Optional[dict] = None, headers: Optional[dict] = None, method: str = "GET", timeout: int = 10) -> Union[dict, str]:
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


def crawl_page(url: str, max_chars: int = 10000, timeout: int = 10) -> Dict[str, str]:
	"""Fetch a single page and return a small dict with title and text snippet.

	If BeautifulSoup is available, uses it to extract the title and visible text.
	Otherwise tries a simple HTML-to-text fallback.
	"""
	if requests is None:
		raise RuntimeError("requests package is required for crawl_page")

	try:
		resp = requests.get(url, timeout=timeout)
		resp.raise_for_status()
		html = resp.text
	except Exception as e:
		return {"url": url, "title": "", "text": f"<error fetching page: {e}>"}

	# Try BeautifulSoup if available
	try:

		soup = BeautifulSoup(html, "html.parser")
		t = soup.title
		title = str(t.string).strip() if t and t.string is not None else ""
		# Extract visible text
		for script in soup(["script", "style"]):
			script.extract()
		# noinspection PyArgumentList
		visible = soup.get_text(separator=" ")
		text = re.sub(r"\s+", " ", visible).strip()
	except ImportError:
		# crude fallback: strip tags
		title_match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
		title = title_match.group(1).strip() if title_match else ""
		# Remove tags
		text = re.sub(r"<[^>]+>", " ", html)
		text = re.sub(r"\s+", " ", text).strip()

	if len(text) > max_chars:
		text = text[:max_chars] + "..."

	return {"url": url, "title": title, "text": text}


def crawl_urls(urls: List[str], delay: float = 0.5, max_chars: int = 10000) -> List[Dict[str, str]]:
	"""Crawl a list of URLs sequentially with an optional delay between requests."""
	out = []
	for u in urls:
		out.append(crawl_page(u, max_chars=max_chars))
		time.sleep(delay)
	return out


def read_file(path: str, encoding: str = "utf-8") -> str:
	"""Read and return the contents of a file. Expands ~ and relative paths."""
	path = os.path.expanduser(path)
	with open(path, "r", encoding=encoding) as fh:
		return fh.read()


def discover_dirs(base_path: str = ".", max_depth: int = 2, include_files: bool = False) -> List[str]:
	"""Discover directories (and optionally files) starting from base_path.

	Returns a list of paths relative to base_path.
	"""
	base_path = os.path.expanduser(base_path)
	base_path = os.path.abspath(base_path)
	results: List[str] = []

	def _walk(current: str, depth: int):
		if depth < 0:
			return
		try:
			with os.scandir(current) as it:
				for entry in it:
					rel = os.path.relpath(entry.path, base_path)
					if entry.is_dir(follow_symlinks=False):
						results.append(rel)
						_walk(entry.path, depth - 1)
					elif include_files and entry.is_file(follow_symlinks=False):
						results.append(rel)
		except PermissionError:
			pass

	_walk(base_path, max_depth)
	return results


def write_markdown(path: str, content: str, encoding: str = "utf-8") -> None:
	"""Write `content` to `path` creating parent directories as needed."""
	path = os.path.expanduser(path)
	d = os.path.dirname(path)
	if d and not os.path.exists(d):
		os.makedirs(d, exist_ok=True)
	with open(path, "w", encoding=encoding) as fh:
		fh.write(content)


__all__ = [
	"get_datetime",
	"duckduckgo_search",
	"generic_http_search",
	"crawl_page",
	"crawl_urls",
	"read_file",
	"discover_dirs",
	"write_markdown",
]
