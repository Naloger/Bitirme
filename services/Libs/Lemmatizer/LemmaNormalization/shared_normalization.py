from __future__ import annotations

import re

DEFAULT_FORBIDDEN: frozenset[str] = frozenset(
	{
		"a", "an", "the", "and", "or", "but", "if", "in", "on", "at",
		"to", "for", "of", "with", "by", "from", "is", "was", "are",
		"were", "be", "been", "being", "have", "has", "had", "do",
		"does", "did", "will", "would", "could", "should", "may", "might",
		"shall", "can", "not", "this", "that", "these", "those", "i",
		"you", "he", "she", "it", "we", "they", "me", "him", "her",
		"us", "them", "my", "your", "his", "its", "our", "their",
	}
)

MIN_WORD_LENGTH = 2
STOPWORD_PATTERNS = frozenset(
	{
		r"^[aeiou]$",  # Single vowels
		r"^m$",  # Turkish suffix artifact
		r"^be$",  # English auxiliary remnant
		r"^a$",  # Article/indefinite marker
	}
)
_COMPILED_STOPWORDS = [re.compile(pattern) for pattern in STOPWORD_PATTERNS]

def _should_filter(token: str) -> bool:
	"""Check if a token should be excluded from lemmatization output."""
	return any(pattern.match(token.lower()) for pattern in _COMPILED_STOPWORDS)

def tokenize_text(text: str) -> list[str]:
	"""Lower-case and split on alphabetic apostrophe tokens."""
	return re.findall(r"[a-z']+", (text or "").lower())

def clean_forbidden(tokens: list[str], forbidden: frozenset[str]) -> list[str]:
	"""Remove forbidden words and tokens shorter than 2 characters."""
	return [token for token in tokens if token not in forbidden and len(token) >= 2]

def normalize_lemmatized_output(tokens: list[str]) -> list[str]:
	"""Filter and normalize lemmatized tokens for cleaner output."""
	normalized: list[str] = []
	for token in tokens:
		cleaned = token.strip()
		if not cleaned:
			continue
		if not re.search(r"[a-zA-Z]", cleaned):
			continue
		if len(cleaned) < MIN_WORD_LENGTH:
			continue
		if _should_filter(cleaned):
			continue
		normalized.append(cleaned)
	return normalized


def normalize_lemmatized_text(text: str) -> str:
	"""Normalize a space-separated string of lemmatized words."""
	return " ".join(normalize_lemmatized_output(text.split()))


__all__ = [
	"DEFAULT_FORBIDDEN",
	"MIN_WORD_LENGTH",
	"STOPWORD_PATTERNS",
	"clean_forbidden",
	"normalize_lemmatized_output",
	"normalize_lemmatized_text",
	"tokenize_text"
]
