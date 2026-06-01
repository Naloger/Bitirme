"""Multilingual lemmatization with language detection and segmentation.

This module builds co-occurrence matrices for multilingual text using advanced
language detection (Stanza) and intelligent text segmentation.

Supported Languages:
    - English (en): Uses spaCy (en_core_web_sm)
    - Turkish (tr): Uses Stanza + optional Zemberek

Adding a New Language:
    1. Create lemmatize_<lang>.py in LemmatizeByLanguage/ with function:
       def lemmatize(text: str) -> list[str]:
           # Return list of normalized lemmas

    2. Import it in this file:
       from services.Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_<lang> import lemmatize as lemmatize_<lang>

    3. Add to LANGUAGE_TO_LEMMATIZER dict:
       LANGUAGE_TO_LEMMATIZER["<lang>"] = lemmatize_<lang>

    The language code ("<lang>") should match the ISO 639-1 standard (e.g., 'fr' for French).
"""

from __future__ import annotations

from typing import Callable

import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

from services.Libs.Lemmatizer.LemmaNormalization.shared_normalization import (
    DEFAULT_FORBIDDEN,
    clean_forbidden,
    normalize_lemmatized_output,
)
from services.Libs.Lemmatizer.LanguageSegmentation.detect_language import (
    detect_text_language,
)
from services.Libs.Lemmatizer.LanguageSegmentation.segment_by_language import (
    LanguageSegment,
    segment_by_language,
)
from services.Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_english import (
    lemmatize as lemmatize_english,
)
from services.Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_turkish import (
    lemmatize as lemmatize_turkish,
)

ENGLISH_MODEL_NAME = "en_core_web_sm"

# Language to lemmatizer mapping - easily extensible for additional languages
# To add support for a new language (e.g., 'lemmatize_xlanguage'):
# 1. Create LemmatizeByLanguage/lemmatize_xlanguage.py with a lemmatize(text: str) -> list[str] function
# 2. Import it: from services.Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_xlanguage import lemmatize as lemmatize_xlanguage
# 3. Add to dict: "xl": lemmatize_xlanguage
LANGUAGE_TO_LEMMATIZER = {
    "en": lemmatize_english,
    "tr": lemmatize_turkish,
    # "xl": lemmatize_xlanguage,  # Uncomment when ready to add xlanguage support
}

# Multilingual corpus with examples in English and Turkish
multilingual_corpus = [
    "The cats are chasing mice.",
    "A cat chasing a mouse is normal.",
    "Merhaba ulan merhaba diyorum adam olun.",
]


class LemmaMatrixBuilder:
    """Build multilingual co-occurrence matrices with language-aware lemmatization."""

    def __init__(
        self,
        language_to_lemmatizer: dict[str, Callable[[str], list[str]]] | None = None,
        default_language: str = "en",
    ) -> None:
        self.language_to_lemmatizer = language_to_lemmatizer or LANGUAGE_TO_LEMMATIZER
        self.default_language = default_language

    def _detect_language(self, text: str) -> str:
        """Best-effort language detection for fallback processing."""
        try:
            segments: list[LanguageSegment] = segment_by_language(text)
            if segments:
                return segments[0]["language"]
        except Exception:
            pass

        try:
            return detect_text_language(text)
        except Exception:
            return self.default_language

    def _segment_text(self, text: str) -> list[LanguageSegment]:
        """Split text into language-specific segments when possible."""
        try:
            return segment_by_language(text)
        except Exception:
            lang = self._detect_language(text)
            return [{"language": lang, "text": text}]

    def _lemmatize_segment(self, segment: LanguageSegment) -> list[str]:
        """Lemmatize one language segment using the configured lemmatizer."""
        lang = segment["language"]
        segment_text = segment["text"]
        lemmatizer = self.language_to_lemmatizer.get(lang, lemmatize_english)

        try:
            return lemmatizer(segment_text) or []
        except Exception:
            return []

    def tokenize(self, text: str) -> list[str]:
        """Automatically segment by language and lemmatize the input text."""
        cleaned_text = text.strip()
        if not cleaned_text:
            return []

        all_lemmas: list[str] = []
        for segment in self._segment_text(cleaned_text):
            all_lemmas.extend(self._lemmatize_segment(segment))

        normalized = normalize_lemmatized_output(all_lemmas)
        return clean_forbidden(normalized, DEFAULT_FORBIDDEN)

    def build_cooccurrence_matrix(self, texts: list[str]):
        """Build the vectorizer and co-occurrence matrix for a list of texts."""
        vectorizer = CountVectorizer(
            tokenizer=self.tokenize, lowercase=False, token_pattern=None
        )
        term_doc_matrix = vectorizer.fit_transform(texts)

        co_occurrence = term_doc_matrix.T * term_doc_matrix
        co_occurrence.setdiag(0)
        return vectorizer, co_occurrence

    def print_co_occurrence_matrix(self, matrix, vectorizer) -> None:
        """Pretty-print a co-occurrence matrix as a pandas DataFrame."""
        words = vectorizer.get_feature_names_out()
        df = pd.DataFrame(matrix.toarray(), columns=words, index=words)

        print("\n--- Word Co-occurrence Matrix ---")
        print(df)


DEFAULT_LEMMA_MATRIX_BUILDER = LemmaMatrixBuilder()


def main() -> None:
    """Build and print the demo co-occurrence matrix with multilingual support."""
    try:
        vectorizer, co_occurrence = DEFAULT_LEMMA_MATRIX_BUILDER.build_cooccurrence_matrix(
            multilingual_corpus
        )
    except RuntimeError as exc:
        print(f"Cannot build the demo co-occurrence matrix: {exc}")
        print(f"Install the spaCy model first: python -m spacy download {ENGLISH_MODEL_NAME}")
        return

    DEFAULT_LEMMA_MATRIX_BUILDER.print_co_occurrence_matrix(co_occurrence, vectorizer)


if __name__ == "__main__":
    main()
