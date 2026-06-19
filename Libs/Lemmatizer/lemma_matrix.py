"""Multilingual lemmatization with language detection and segmentation.

Supported Languages:
    - English (en): Uses spaCy (en_core_web_sm)
    - Turkish (tr): Uses Stanza + optional Zemberek

Adding a New Language:
    1. Create lemmatize_<lang>.py in LemmatizeByLanguage/ with:
           def lemmatize(text: str) -> list[str]: ...

    2. Import and register it here:
           from services.Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_<lang> import lemmatize as lemmatize_<lang>
           LANGUAGE_TO_LEMMATIZER["<lang>"] = lemmatize_<lang>

    Language codes follow ISO 639-1 (e.g. 'fr' for French).
"""

from __future__ import annotations

import logging
from typing import Callable

import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

from Libs.Lemmatizer.LanguageSegmentation.detect_language import (
    detect_text_language,
)
from Libs.Lemmatizer.LanguageSegmentation.segment_by_language import (
    LanguageSegment,
    segment_by_language,
)
from Libs.Lemmatizer.LemmaNormalization.shared_normalization import (
    DEFAULT_FORBIDDEN,
    clean_forbidden,
    normalize_lemmatized_output,
)
from Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_english import (
    lemmatize as lemmatize_english,
)
from Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_turkish import (
    lemmatize as lemmatize_turkish,
)

LANGUAGE_TO_LEMMATIZER: dict[str, Callable[[str], list[str]]] = {
    "en": lemmatize_english,
    "tr": lemmatize_turkish,
}

logger = logging.getLogger(__name__)

class LemmaMatrixBuilder:
    """Build multilingual co-occurrence matrices with language-aware lemmatization."""

    def __init__(
        self,
        language_to_lemmatizer: dict[str, Callable[[str], list[str]]] | None = None,
        default_language: str = "en",
    ) -> None:
        self.language_to_lemmatizer = language_to_lemmatizer or LANGUAGE_TO_LEMMATIZER
        self.default_language = default_language

    def _segment_text(self, text: str) -> list[LanguageSegment]:
        """Split text into language-specific segments, with fallback to whole-text detection."""
        try:
            return segment_by_language(text)
        except Exception as e:
            logger.debug("segment_by_language failed, falling back to single language detection: %s", e)

        try:
            lang = detect_text_language(text)
        except Exception as e:
            logger.warning("detect_text_language failed, using 'gibberish' as fallback: %s", e)
            lang = "gibberish"

        return [{"language": lang, "text": text}]

    def _lemmatize_segment(self, segment: LanguageSegment) -> list[str]:
        """Lemmatize one language segment using the appropriate lemmatizer."""
        lang = segment["language"]
        if lang == "gibberish":
            return ["gibberish"] * len(segment["text"].split())

        lemmatizer = self.language_to_lemmatizer.get(lang, lemmatize_english)
        try:
            return lemmatizer(segment["text"]) or []
        except Exception as e:
            logger.error(
                "Lemmatizer failed for language '%s': %s. Returning gibberish.",
                lang,
                e
            )
            return ["gibberish"] * len(segment["text"].split())

    def tokenize(self, text: str) -> list[str]:
        """Segment by language, lemmatize, and normalize the input text."""
        cleaned = text.strip()
        if not cleaned:
            return []

        lemmas: list[str] = []
        for segment in self._segment_text(cleaned):
            lemmas.extend(self._lemmatize_segment(segment))

        normalized = normalize_lemmatized_output(lemmas)
        filtered = [l for l in normalized if l != "gibberish"]
        return clean_forbidden(filtered, DEFAULT_FORBIDDEN)

    def build_cooccurrence_matrix(self, texts: list[str]):
        """Build and return a (vectorizer, co-occurrence matrix) pair for the given texts."""
        vectorizer = CountVectorizer(
            tokenizer=self.tokenize, lowercase=False, token_pattern=None
        )
        term_doc = vectorizer.fit_transform(texts)
        co_occurrence = term_doc.T * term_doc
        co_occurrence.setdiag(0)
        return vectorizer, co_occurrence

    @staticmethod
    def print_cooccurrence_matrix(matrix, vectorizer) -> None:
        """Pretty-print a co-occurrence matrix as a pandas DataFrame."""
        try:
            words = vectorizer.get_feature_names_out()
            df = pd.DataFrame(matrix.toarray(), columns=words, index=words)
            matrix_text = df.to_string()
            logger.info("Word Co-occurrence Matrix:\n%s", matrix_text)
            print("\n"+"="*70)
            print("\n--- Word Co-occurrence Matrix ---")
            print(matrix_text)
            print("\n"+"="*70)
        except (ValueError, AttributeError, RuntimeError, TypeError) as e:
            logger.error("Failed to print cooccurrence matrix: %s", e)

    @staticmethod
    def extract_matrix_pairs(matrix, vectorizer) -> list[dict[str, str | int]]:
        """
        Extract word pairs and their weights, printing them and returning
        the data in a structured format suitable for SQL/DB insertion.
        """
        pairs = []

        try:
            words = vectorizer.get_feature_names_out()
            # Convert to COOrdinate format for highly efficient iteration over non-zero elements
            coo = matrix.tocoo()

            # We filter for i < j because the co-occurrence matrix is symmetric.
            # This prevents duplicate pairs (e.g., A-B and B-A).
            for i, j, weight in zip(coo.row, coo.col, coo.data):
                if i < j:
                    pairs.append({
                        "word1": words[i],
                        "word2": words[j],
                        "weight": int(weight)
                    })

            return pairs

        except (ValueError, AttributeError, RuntimeError, TypeError) as e:
            logger.error("Failed to extract and print co-occurrence pairs: %s", e)
            return []

    @staticmethod
    def print_matrix_pairs(matrix, vectorizer):
        # FIX: Replaced MatrixProcessor with the actual class name
        pairs = LemmaMatrixBuilder.extract_matrix_pairs(matrix, vectorizer)

        if not pairs:
            print("No pairs extracted or an error occurred.")
            return []

        # Sort the pairs by weight (highest frequency first)
        pairs.sort(key=lambda x: x["weight"], reverse=True)

        print("=" * 70)
        print("--- Extracted Word Pairs & Weights ---")
        for pair in pairs:
            print(f"{pair['word1']} <-> {pair['word2']} : {pair['weight']}")
        print("=" * 70)

        return pairs