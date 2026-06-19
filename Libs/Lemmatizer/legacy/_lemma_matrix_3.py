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

import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

from Libs.Lemmatizer.LemmaNormalization.shared_normalization import (
    DEFAULT_FORBIDDEN,
    clean_forbidden,
    normalize_lemmatized_output,
)
from Libs.Lemmatizer.LanguageSegmentation.detect_language import (
    detect_text_language,
)
from Libs.Lemmatizer.LanguageSegmentation.segment_by_language import (
    segment_by_language,
    LanguageSegment,
)
from Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_english import (
    lemmatize as lemmatize_english,
)
from Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_turkish import (
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



def _multilingual_lemmatize_tokenizer(text: str) -> list[str]:
    """Automatically segment by language and lemmatize the input text.

    Uses advanced Stanza-based language detection and segmentation for multilingual texts.
    Supports English, Turkish, and can be extended for additional languages.

    Process:
        1. Segment text into language-specific chunks using detect_text_language
        2. Lemmatize each segment with its language-appropriate lemmatizer
        3. Apply shared normalizations and filter stopwords

    Returns a list of cleaned tokens suitable for CountVectorizer.
    """
    cleaned = text.strip()
    if not cleaned:
        return []

    try:
        segments: list[LanguageSegment] = segment_by_language(cleaned)
    except Exception:
        try:
            lang = detect_text_language(cleaned)
        except Exception:
            lang = "en"
        segments = [{"language": lang, "text": cleaned}]

    all_lemmas: list[str] = []

    # Process each language segment
    for segment in segments:
        lang = segment["language"]
        segment_text = segment["text"]

        # Get the appropriate lemmatizer function
        # Default to English if language not supported
        lemmatizer = LANGUAGE_TO_LEMMATIZER.get(lang, lemmatize_english)

        try:
            lemmas = lemmatizer(segment_text)
            if lemmas:
                all_lemmas.extend(lemmas)
        except Exception:
            # Skip this segment if lemmatization fails
            # but continue processing other segments
            continue

    # Filter and normalize lemma tokens (strips, removes short/non-alpha tokens, stop patterns)
    normalized = normalize_lemmatized_output(all_lemmas)
    # Remove common forbidden words (stopwords) defined by the project
    cleaned = clean_forbidden(normalized, DEFAULT_FORBIDDEN)
    return cleaned


def build_cooccurrence_matrix(texts: list[str]):
    """Build the vectorizer and co-occurrence matrix for a list of texts.

    Automatically detects the language of each text and applies appropriate lemmatization.
    Supports English and Turkish.
    """
    vectorizer = CountVectorizer(
        tokenizer=_multilingual_lemmatize_tokenizer, lowercase=False, token_pattern=None
    )
    term_doc_matrix = vectorizer.fit_transform(texts)

    co_occurrence = term_doc_matrix.T * term_doc_matrix
    co_occurrence.setdiag(0)  # Zero out self-co-occurrence
    return vectorizer, co_occurrence


# 4. Print Matrix Function
def print_co_occurrence_matrix(matrix, vectorizer):
    # Get the feature names (the lemmas) to use as labels
    words = vectorizer.get_feature_names_out()

    # Convert the sparse matrix to a dense pandas DataFrame
    df = pd.DataFrame(matrix.toarray(), columns=words, index=words)

    print("\n--- Word Co-occurrence Matrix ---")
    print(df)


def main() -> None:
    """Build and print the demo co-occurrence matrix with multilingual support."""
    try:
        vectorizer, co_occurrence = build_cooccurrence_matrix(multilingual_corpus)
    except RuntimeError as exc:
        print(f"Cannot build the demo co-occurrence matrix: {exc}")
        print(f"Install the spaCy model first: python -m spacy download {ENGLISH_MODEL_NAME}")
        return

    print_co_occurrence_matrix(co_occurrence, vectorizer)


if __name__ == "__main__":
    main()
