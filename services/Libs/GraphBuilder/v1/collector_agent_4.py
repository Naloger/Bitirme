"""
TextNormalizer  (simplified)
============================
Pipeline: spaCy pipe → co-occurrence → PPMI → FastAPI persist

Key simplifications vs. original
---------------------------------
· spaCy replaces the three-pass tokenize / clean / lemmatize chain.
  One nlp() call does tokenisation, stopword removal, punctuation filtering,
  and lemmatisation simultaneously.
· numpy vectorisation replaces the scalar PPMI loop.
  Marginal probabilities are computed with array sums; the score matrix is
  filled in one broadcast operation instead of a per-pair loop.
· pydantic models replace raw dicts for every HTTP payload and response,
  giving free validation and IDE auto-complete.
· httpx replaces requests (async-ready, cleaner API, built-in raise_for_status).

Dependencies
------------
    pip install spacy httpx pydantic numpy
    python -m spacy download en_core_web_sm
"""

from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from collections import Counter, defaultdict
from typing import Any, Optional

import httpx
import numpy as np
import spacy
from pydantic import BaseModel

from services.Libs.GraphBuilder.v2.api_models import (
    KeywordRecord,
    KeywordsPayload,
    PpmiPairRecord,
    PpmiPayload,
)
from services.Libs.Lemmatizer.LanguageSegmentation.segment_by_language import (
    segment_by_language,
)
from services.Libs.Lemmatizer.LemmaNormalization.shared_normalization import (
    build_cooccurrence,
    calculate_ppmi,
)

# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class TextNormalizer:
    """
    Parameters
    ----------
    window_size : int
        Tokens on each side of a pivot for co-occurrence counting.
    ppmi_threshold : float
        Minimum PPMI score to retain a pair.
    api_base_url : str
        Base URL for the local FastAPI collector service.
    timeout : float
        HTTP timeout in seconds.
    extra_forbidden : set[str] | None
        Extra stopwords merged with spaCy's built-in list.
    spacy_model : str
        spaCy model name.  Defaults to ``en_core_web_sm``.
    """

    def __init__(
        self,
        window_size: int = 1,
        ppmi_threshold: float = 0.0,
        api_base_url: str = "http://127.0.0.1:8000/api/collector",
        timeout: float = 10.0,
        extra_forbidden: Optional[set[str]] = None,
        spacy_model: str = "en_core_web_sm",
        language_model_map: Optional[dict[str, str]] = None,
        default_language: str = "en",
    ) -> None:
        self.window_size = window_size
        self.ppmi_threshold = ppmi_threshold
        self.timeout = timeout
        self.default_language = default_language
        self._extra_forbidden = frozenset(extra_forbidden or ())
        self._language_model_map = {
            default_language: spacy_model,
            **(language_model_map or {}),
        }
        self._nlp_cache: dict[str, Any] = {}
        self._language: str = default_language
        self._language_model: str = spacy_model

        self._client = httpx.Client(
            base_url=api_base_url.rstrip("/"),
            timeout=timeout,
        )

        # Populated by normalize_text()
        self._cooccurrence: dict[tuple[str, str], int] = {}
        self._vocab: list[str] = []

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def normalize_text(self, text: str) -> list[tuple[str, int]]:
        """
        Run the full pipeline and return (keyword, frequency) pairs.

        Side-effects: populates self._cooccurrence, self._vocab, and the
        language/model metadata used by save().
        """
        segments = segment_by_language(text)
        if not segments:
            self._cooccurrence = {}
            self._vocab = []
            self._language = self.default_language
            self._language_model = self._language_model_map[self.default_language]
            return []

        tokens: list[str] = []
        cooccurrence: dict[tuple[str, str], int] = defaultdict(int)
        languages: set[str] = set()
        models: set[str] = set()

        for segment in segments:
            language = segment["language"]
            segment_text = segment["text"].strip()
            if not segment_text:
                continue

            model_name = self._language_model_map.get(language)
            if model_name is None:
                raise RuntimeError(
                    f"No spaCy model configured for language '{language}'"
                )

            nlp = self.__load_nlp(model_name)
            doc = nlp(segment_text.lower())
            segment_tokens = [
                t.lemma_
                for t in doc
                if not t.is_stop and not t.is_punct and len(t.lemma_) >= 2
            ]
            if not segment_tokens:
                continue

            tokens.extend(segment_tokens)
            languages.add(language)
            models.add(model_name)
            for pair, count in self.__build_cooccurrence(segment_tokens).items():
                cooccurrence[pair] += count

        if not tokens:
            self._cooccurrence = {}
            self._vocab = []
            self._language = self.default_language
            self._language_model = self._language_model_map[self.default_language]
            return []

        counts = Counter(tokens)
        self._vocab = sorted(counts)
        self._cooccurrence = dict(cooccurrence)
        self._language = next(iter(languages)) if len(languages) == 1 else "mixed"
        self._language_model = (
            next(iter(models)) if len(models) == 1 else "mixed"
        )

        return counts.most_common()

    # ------------------------------------------------------------------
    # Stage 1 – co-occurrence
    # ------------------------------------------------------------------

    def __build_cooccurrence(
        self, tokens: list[str]
    ) -> dict[tuple[str, str], int]:
        """Sliding-window co-occurrence (pairs stored in sorted order)."""
        return build_cooccurrence(tokens, self.window_size)

    # ------------------------------------------------------------------
    # Stage 2 – PPMI (vectorised)
    # ------------------------------------------------------------------

    def __print_matrix(vocab: list[str], matrix: np.ndarray) -> None:
        """Pretty-print a small PPMI matrix for the demo entry point."""
        if matrix.size == 0:
            print("(empty matrix)")
            return

        header = " " * 12 + " ".join(f"{term:>8}" for term in vocab)
        print(header)
        for term, row in zip(vocab, matrix):
            values = " ".join(f"{value:8.3f}" for value in row)
            print(f"{term:>10}  {values}")

    def __ppmi_pairs(self) -> list[PpmiPairRecord]:
        """Return filtered PPMI pairs as pydantic records."""
        vocab: list[str]
        vocab, matrix = self.to_ppmi_matrix()
        pairs: list[PpmiPairRecord] = []
        rows, cols = np.where(matrix > 0)
        for i, j in zip(rows, cols):
            if i < j:   # upper triangle only (symmetric)
                term_a = str(vocab[int(i)])
                term_b = str(vocab[int(j)])
                score = float(matrix[int(i), int(j)])
                pairs.append(PpmiPairRecord(term_a=term_a, term_b=term_b, score=score))
        return pairs


    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def __post(self, path: str, payload: BaseModel) -> None:
        try:
            self._client.post(path, content=payload.model_dump_json(), headers={"Content-Type": "application/json"}).raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"POST {path} failed") from exc

    def __get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            r = self._client.get(path, params=params)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"GET {path} failed") from exc

    def __load_nlp(self, model_name: str) -> Any:
        nlp = self._nlp_cache.get(model_name)
        if nlp is not None:
            return nlp

        try:
            nlp = spacy.load(model_name)
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"spaCy model '{model_name}' is not available") from exc

        for word in self._extra_forbidden:
            nlp.vocab[word].is_stop = True

        self._nlp_cache[model_name] = nlp
        return nlp


    def to_ppmi_matrix(self) -> tuple[list[str], np.ndarray]:
        """
        Build a symmetric (vocab × vocab) PPMI matrix.

        Returns
        -------
        vocab  : list[str]
        matrix : np.ndarray, shape (V, V), dtype float32
        """
        if not self._cooccurrence:
            raise RuntimeError("Call normalize_text() first.")

        return calculate_ppmi(self._cooccurrence, self.ppmi_threshold)

    # ------------------------------------------------------------------
    # Stage 3 – API helpers (httpx + pydantic)
    # ------------------------------------------------------------------

    def save(self, keyword_counts: list[tuple[str, int]]) -> None:
        """POST keyword counts and PPMI pairs to the FastAPI backend."""
        kw_payload = KeywordsPayload(
            keywords=[
                KeywordRecord(
                    term=t,
                    count=c,
                    language=self._language,
                    language_model=self._language_model,
                )
                for t, c in keyword_counts
            ]
        )
        pp_payload = PpmiPayload(
            ppmi_pairs=[
                PpmiPairRecord(
                    term_a=pair.term_a,
                    term_b=pair.term_b,
                    score=pair.score,
                    language=self._language,
                    language_model=self._language_model,
                )
                for pair in self.__ppmi_pairs()
            ]
        )

        self.__post("/keywords", kw_payload)
        self.__post("/ppmi-pairs", pp_payload)

    def retrieve(
        self,
        *,
        min_count: int = 1,
        min_ppmi: float = 0.0,
        top_k: Optional[int] = None,
        term: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict[str, object]:
        """GET keywords and PPMI pairs from the FastAPI backend."""
        kw_params: dict[str, Any] = {"min_count": min_count}
        if top_k is not None:
            kw_params["top_k"] = int(top_k)
        if term is not None:
            kw_params["term"] = term
        if language is not None:
            kw_params["language"] = language

        pp_params: dict[str, Any] = {"min_ppmi": min_ppmi}
        if term is not None:
            pp_params["term"] = term
        if language is not None:
            pp_params["language"] = language

        kw_data = self.__get("/keywords", kw_params)
        pp_data = self.__get("/ppmi-pairs", pp_params)

        return {
            "keywords":   KeywordsPayload(**kw_data).keywords,
            "ppmi_pairs": PpmiPayload(**pp_data).ppmi_pairs,
        }

    def load_ppmi_matrix(self, language: Optional[str] = None) -> tuple[list[str], np.ndarray]:
        """Reconstruct a PPMI matrix from stored API rows."""
        params: dict[str, Any] = {"min_ppmi": 0.0}
        if language is not None:
            params["language"] = language

        data  = self.__get("/ppmi-pairs", params)
        pairs = PpmiPayload(**data).ppmi_pairs

        if not pairs:
            return [], np.zeros((0, 0), dtype=np.float32)

        vocab = sorted({p.term_a for p in pairs} | {p.term_b for p in pairs})
        idx   = {w: i for i, w in enumerate(vocab)}
        mat   = np.zeros((len(vocab), len(vocab)), dtype=np.float32)

        for p in pairs:
            i, j = idx[p.term_a], idx[p.term_b]
            mat[i, j] = mat[j, i] = p.score

        return vocab, mat


