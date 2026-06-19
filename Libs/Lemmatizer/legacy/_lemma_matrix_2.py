from __future__ import annotations

import pandas as pd
from langdetect import detect, LangDetectException
from sklearn.feature_extraction.text import CountVectorizer

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

ENGLISH_MODEL_NAME = "en_core_web_sm"
LANGUAGE_TO_LEMMATIZER = {
    "en": lemmatize_english,
    "tr": lemmatize_turkish,
}

# Multilingual corpus with examples in English and Turkish
multilingual_corpus = [
    "The cats are chasing mice.",
    "A cat chasing a mouse is normal.",
    "Merhaba ulan merhaba diyorum adam olun.",
]

# 2. Vectorization
# Note: passed token_pattern=None to avoid warnings when using a custom tokenizer
def _detect_language(text: str) -> str:
    """Detect the language of the input text.

    Args:
        text: Input text to detect language for

    Returns:
        Language code (e.g., 'en' for English, 'tr' for Turkish)
        Defaults to 'en' if detection fails
    """
    try:
        detected = detect(text)
        # Map detected language code to our supported languages
        if detected in LANGUAGE_TO_LEMMATIZER:
            return detected
        # Default to English if detected language isn't supported
        return "en"
    except LangDetectException:
        # Default to English if detection fails
        return "en"


def _multilingual_lemmatize_tokenizer(text: str) -> list[str]:
    """Automatically detect language and lemmatize the input text.

    Supports English and Turkish. Applies shared normalizations.

    Returns a list of cleaned tokens suitable for CountVectorizer.
    """
    # Detect the language
    lang = _detect_language(text)

    # Get the appropriate lemmatizer function
    lemmatizer = LANGUAGE_TO_LEMMATIZER.get(lang, lemmatize_english)

    # Lemmatize using the detected language
    lemmas = lemmatizer(text)

    # Filter and normalize lemma tokens (strips, removes short/non-alpha tokens, stop patterns)
    normalized = normalize_lemmatized_output(lemmas)
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
