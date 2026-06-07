"""
TextNormalizer
==============
Pipeline: clean → lemmatize → co-occurrence → PPMI score → FastAPI persist

Stages
------
1. normalize_text()        – public entry point, returns keyword frequency list
   · _clean_forbidden()    – strip stopwords + forbidden tokens
   · _lemmatize()          – reduce tokens to base form (spaCy or NLTK)
   · _build_cooccurrence() – sliding-window pair counts

2. PPMI helpers (stateless transforms on the co-occurrence dict)
   · _calculate_ppmi()     – raw counts → PPMI score matrix
   · _filter_by_ppmi()     – discard pairs below threshold
   · to_ppmi_matrix()      – dict → 2-D numpy array (symmetric, vocab-indexed)

3. API helpers
   · save()                – POST keywords + PPMI matrix rows to FastAPI
   · retrieve()            – GET by term, min_count, min_ppmi, top_k
   · load_ppmi_matrix()    – GET PPMI rows → numpy array (inverse of to_ppmi_matrix)
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Optional

import numpy as np
import requests

from services.Libs.Lemmatizer.LemmaNormalization.shared_normalization import (
	DEFAULT_FORBIDDEN,
	build_cooccurrence,
	calculate_ppmi,
	clean_forbidden,
	fallback_lemmatizer,
	ppmi_scores_from_cooccurrence,
	records_from_payload,
	tokenize_text,
)


class TextNormalizer:
	"""
    Parameters
    ----------
    window_size : int
        Number of tokens on each side of a pivot for co-occurrence counting.
        Defaults to 2.
    ppmi_threshold : float
        Minimum PPMI value to retain a keyword pair.  Defaults to 0.0
        (keeps all positive PMI; raise to e.g. 1.0 for stricter filtering).
    api_base_url : str
        Base URL for the local FastAPI service.
        Example: ``http://127.0.0.1:8000/api/collector``
    timeout : float
        Request timeout in seconds for each HTTP call.
    extra_forbidden : set[str] | None
        Additional tokens to treat as forbidden (merged with the built-in list).
    lemmatizer : callable[[list[str]], list[str]] | None
        Drop-in lemmatizer.  Receives a token list, returns a token list.
        If None, a simple suffix-stripping fallback is used.
    """

	def __init__(
			self,
			window_size: int = 1,
			ppmi_threshold: float = 0.0,
			api_base_url: str = "http://127.0.0.1:8000/api/collector",
			timeout: float = 10.0,
			extra_forbidden: Optional[set[str]] = None,
			lemmatizer=None,
	) -> None:
		self.window_size = window_size
		self.ppmi_threshold = ppmi_threshold
		self.api_base_url = api_base_url.rstrip("/")
		self.timeout = timeout
		self._lemmatizer = lemmatizer or self._fallback_lemmatizer
		self.forbidden: frozenset[str] = (
			DEFAULT_FORBIDDEN | frozenset(w.lower() for w in extra_forbidden)
			if extra_forbidden
			else DEFAULT_FORBIDDEN
		)

		# Internal state populated by normalize_text()
		self._cooccurrence: dict[tuple[str, str], int] = {}
		self._vocab: list[str] = []

	# -----------------------------------------------------------------------
	# Public entry point
	# -----------------------------------------------------------------------

	def normalize_text(self, text: str) -> list[tuple[str, int]]:
		"""
        Full preprocessing pipeline.

        Returns
        -------
        list[tuple[str, int]]
            Sorted list of (keyword, frequency) pairs, highest count first.

        Side-effects
        ------------
        Populates ``self._cooccurrence`` and ``self._vocab`` for downstream
        PPMI methods.
        """
		tokens = self._tokenize(text)
		tokens = self._clean_forbidden(tokens)
		tokens = self._lemmatize(tokens)

		if not tokens:
			return []

		counts = Counter(tokens)
		self._vocab = sorted(counts)                      # stable vocab order
		self._cooccurrence = self._build_cooccurrence(tokens)

		return counts.most_common()                       # (keyword, count)

	# -----------------------------------------------------------------------
	# Stage 1 – preprocessing helpers
	# -----------------------------------------------------------------------

	@staticmethod
	def _tokenize(text: str) -> list[str]:
		"""Lower-case and split on non-alphanumeric characters."""
		return tokenize_text(text)

	def _clean_forbidden(self, tokens: list[str]) -> list[str]:
		"""Remove forbidden words and tokens shorter than 2 characters."""
		return clean_forbidden(tokens, self.forbidden)

	def _lemmatize(self, tokens: list[str]) -> list[str]:
		"""Delegate to the configured lemmatizer."""
		return self._lemmatizer(tokens)

	@staticmethod
	def _fallback_lemmatizer(tokens: list[str]) -> list[str]:
		"""
        Minimal suffix-stripping lemmatizer.
        For production use, replace with spaCy:
            nlp = spacy.load("en_core_web_sm")
            return [t.lemma_ for t in nlp(" ".join(tokens))]
        """
		return fallback_lemmatizer(tokens)

	def _api_url(self, path: str) -> str:
		"""Build an absolute URL for a collector endpoint."""
		return f"{self.api_base_url}/{path.lstrip('/')}"

	def _request(
			self,
			method: str,
			path: str,
			*,
			params: dict[str, Any] | None = None,
			json: dict[str, Any] | None = None,
	) -> dict[str, Any]:
		"""Send a JSON request to the FastAPI collector and validate the response."""
		try:
			response = requests.request(
				method,
				self._api_url(path),
				params=params,
				json=json,
				timeout=self.timeout,
			)
			response.raise_for_status()
		except requests.RequestException as exc:
			raise RuntimeError(
				f"Collector API request failed: {method} {self._api_url(path)}"
			) from exc

		try:
			payload = response.json()
		except ValueError as exc:
			raise RuntimeError(
				f"Collector API returned invalid JSON: {method} {self._api_url(path)}"
			) from exc

		if not isinstance(payload, dict):
			raise RuntimeError(
				f"Collector API returned unexpected payload type: {type(payload).__name__}"
			)

		return payload

	@staticmethod
	def _records_from_payload(
			payload: dict[str, Any], key: str
	) -> list[dict[str, Any]]:
		"""Extract a list of record objects from a JSON response."""
		return records_from_payload(payload, key)

	def _build_cooccurrence(
			self, tokens: list[str]
	) -> dict[tuple[str, str], int]:
		"""
        Sliding-window co-occurrence counts.

        For each pivot token, every token within ``window_size`` positions on
        either side forms a pair.  Pairs are stored in sorted order so
        (a, b) and (b, a) map to the same key.
        """
		return build_cooccurrence(tokens, self.window_size)

	# -----------------------------------------------------------------------
	# Stage 2 – PPMI scoring
	# -----------------------------------------------------------------------

	def _calculate_ppmi(self) -> dict[tuple[str, str], float]:
		"""
        Compute Positive PMI for each co-occurring pair.

        PPMI(a, b) = max(0, log2( P(a,b) / (P(a) * P(b)) ))

        Requires ``normalize_text()`` to have been called first.
        """
		if not self._cooccurrence:
			raise RuntimeError("Call normalize_text() before calculate_ppmi().")

		return ppmi_scores_from_cooccurrence(self._cooccurrence, self.ppmi_threshold)

	def _filter_by_ppmi(
			self, ppmi_scores: dict[tuple[str, str], float]
	) -> dict[tuple[str, str], float]:
		"""Return only pairs whose PPMI exceeds ``self.ppmi_threshold``."""
		return {
			pair: score
			for pair, score in ppmi_scores.items()
			if score > self.ppmi_threshold
		}

	def to_ppmi_matrix(self) -> tuple[list[str], np.ndarray]:
		"""
        Build a symmetric (vocab × vocab) PPMI matrix.

        Returns
        -------
        vocab : list[str]
            Ordered list of terms; matrix row/col index matches this list.
        matrix : np.ndarray, shape (V, V), dtype float32
            PPMI scores; unobserved pairs have value 0.
        """
		return calculate_ppmi(self._cooccurrence, self.ppmi_threshold)

	def save(self, keyword_counts: list[tuple[str, int]]) -> None:
		"""
        Upsert keyword counts and PPMI scores through the FastAPI backend.

        Existing keyword counts are incremented (not replaced) so repeated
        calls accumulate.
        """
		ppmi_scores = self._filter_by_ppmi(self._calculate_ppmi())
		keywords_payload = {
			"keywords": [{"term": term, "count": count} for term, count in keyword_counts]
		}
		pairs_payload = {
			"ppmi_pairs": [
				{"term_a": a, "term_b": b, "score": score}
				for (a, b), score in ppmi_scores.items()
			]
		}

		self._request("POST", "/keywords", json=keywords_payload)
		self._request("POST", "/ppmi-pairs", json=pairs_payload)

	def retrieve(
			self,
			*,
			min_count: int = 1,
			min_ppmi: float = 0.0,
			top_k: Optional[int] = None,
			term: Optional[str] = None,
	) -> dict[str, object]:
		"""
        Query the FastAPI backend for stored keywords and PPMI pairs.

        Parameters
        ----------
        min_count : int
            Only return keywords with at least this frequency.
        min_ppmi : float
            Only return PPMI pairs with at least this score.
        top_k : int | None
            If set, return only the top-k keywords by count.
        term : str | None
            If set, return only rows where term_a or term_b matches.

        Returns
        -------
        dict with keys:
            "keywords" : list[tuple[str, int]]
            "ppmi_pairs" : list[tuple[str, str, float]]
        """
		keyword_params: dict[str, Any] = {"min_count": min_count}
		if top_k is not None:
			keyword_params["top_k"] = int(top_k)
		if term is not None:
			keyword_params["term"] = term

		pair_params: dict[str, Any] = {"min_ppmi": min_ppmi}
		if term is not None:
			pair_params["term"] = term

		keywords_payload = self._request("GET", "/keywords", params=keyword_params)
		ppmi_payload = self._request("GET", "/ppmi-pairs", params=pair_params)
		keywords = self._records_from_payload(keywords_payload, "keywords")
		ppmi_pairs = self._records_from_payload(ppmi_payload, "ppmi_pairs")

		return {"keywords": keywords, "ppmi_pairs": ppmi_pairs}

	def load_ppmi_matrix(self) -> tuple[list[str], np.ndarray]:
		"""
        Reconstruct a PPMI matrix from API rows.

        This is the inverse of ``to_ppmi_matrix()`` and lets you resume work
        from a previous session without reprocessing raw text.
        """
		payload = self._request("GET", "/ppmi-pairs", params={"min_ppmi": 0.0})
		pairs = self._records_from_payload(payload, "ppmi_pairs")

		if not pairs:
			return [], np.zeros((0, 0), dtype=np.float32)

		vocab = sorted(
			{
				str(term)
				for pair in pairs
				for term in (pair["term_a"], pair["term_b"])
			}
		)
		idx = {word: i for i, word in enumerate(vocab)}
		v_size = len(vocab)
		matrix = np.zeros((v_size, v_size), dtype=np.float32)
		for pair in pairs:
			a = str(pair["term_a"])
			b = str(pair["term_b"])
			score = float(pair["score"])
			i, j = idx[a], idx[b]
			matrix[i, j] = score
			matrix[j, i] = score

		return vocab, matrix
