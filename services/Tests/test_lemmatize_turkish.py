# -*- coding: utf-8 -*-
"""Tests for lemmatize_turkish module with logging instrumentation."""
import logging
import sys
from pathlib import Path

# Add the inner services package root to path so direct script execution works.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_turkish import (
    _candidate_is_plausible,
    _normalize_candidate,
    lemmatize,
)
from services.Tests.test_helpers import trace_call

# Configure logging for test output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_simple_sentence():
    """Test lemmatization of simple Turkish sentence."""
    text = "Kediler hızlı koşuyorlar."
    logger.info(f"Testing simple Turkish sentence: {text}")
    result = trace_call(lemmatize, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    if len(result) == 0:
        raise AssertionError("Expected non-empty list")
    if not all(isinstance(item, str) for item in result):
        raise AssertionError("Expected all items to be strings")
    print("✓ test_simple_sentence passed")


def test_empty_string():
    """Test with empty string."""
    text = ""
    logger.info("Testing empty Turkish string")
    result = trace_call(lemmatize, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    if result:
        raise AssertionError(f"Expected empty list, got {result}")
    print("✓ test_empty_string passed")


def test_single_word():
    """Test with single word."""
    text = "koşuyor"
    logger.info(f"Testing single Turkish word: {text}")
    result = trace_call(lemmatize, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_single_word passed")


def test_multiple_sentences():
    """Test with multiple sentences."""
    text = "Ben koşuyorum. Sen yürüyorsun. Onlar atlıyorlar."
    logger.info("Testing multiple Turkish sentences")
    result = trace_call(lemmatize, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    if len(result) < 1:
        raise AssertionError(f"Expected at least 1 item, got {len(result)}")
    print("✓ test_multiple_sentences passed")


def test_with_punctuation():
    """Test text with various punctuation marks."""
    text = "Ne yapıyorsun? Ben koşuyorum, atlıyorum ve yürüyorum!"
    logger.info("Testing Turkish text with punctuation")
    result = trace_call(lemmatize, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_with_punctuation passed")


def test_verb_forms():
    """Test lemmatization of various verb forms."""
    text = "koşuyor koşuyorum koştum koşacak."
    logger.info("Testing Turkish verb forms")
    result = trace_call(lemmatize, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_verb_forms passed")


def test_mixed_case():
    """Test with mixed case text."""
    text = "KOŞUYOR hızlı Koşuyor yavaş koşuyor daha hızlı."
    logger.info("Testing Turkish mixed case text")
    result = trace_call(lemmatize, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_mixed_case passed")


def test_with_numbers():
    """Test text containing numbers."""
    text = "Benim 3 kedim ve 5 köpeğim var."
    logger.info("Testing Turkish text with numbers")
    result = trace_call(lemmatize, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_with_numbers passed")


def test_return_type():
    """Test that return type is always list of strings."""
    texts = ["merhaba dünya", "sınav", "", "Türk dilinde cümle"]
    logger.info("Testing Turkish return type validation")
    for i, text in enumerate(texts):
        result = trace_call(lemmatize, text, label=f"lemmatize[{i}]")
        if not isinstance(result, list):
            raise AssertionError(f"Expected list for text[{i}], got {result}")
        if not all(isinstance(item, str) for item in result):
            raise AssertionError(f"Expected all items to be strings for text[{i}]")
        logger.info(f"Turkish return type valid for text[{i}]: {len(result)} items")
    print("✓ test_return_type passed")


def test_newline_separated_sentences():
    """Test with newline-separated sentences."""
    text = "İlk cümle.\nİkinci cümle.\nÜçüncü cümle."
    logger.info("Testing Turkish newline-separated sentences")
    result = trace_call(lemmatize, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_newline_separated_sentences passed")


def test_turkish_diacritics():
    """Test handling of Turkish diacritics."""
    text = "Türkçe karakterler: ç, ğ, ı, ö, ş, ü"
    logger.info("Testing Turkish diacritics handling")
    result = trace_call(lemmatize, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_turkish_diacritics passed")


def test_normalize_candidate_mojibake():
    """Mojiake-like inputs should be normalized safely."""
    candidate = _normalize_candidate("kÃ¶pek+Noun+A3sg")
    if candidate != "köpek":
        raise AssertionError(f"Expected 'köpek', got {candidate!r}")
    print("✓ test_normalize_candidate_mojibake passed")


def test_candidate_plausibility_filters_fragments():
    """Broken or unrelated Zemberek candidates should be rejected."""
    if _candidate_is_plausible("v", "sınav", "sınav"):
        raise AssertionError("Expected single-letter fragment to be rejected")
    if _candidate_is_plausible("kohun", "koşuyor", "koşuyor"):
        raise AssertionError("Expected unrelated candidate to be rejected")
    if not _candidate_is_plausible("koş", "koşuyor", "koşuyor"):
        raise AssertionError("Expected plausible stem to be accepted")
    print("✓ test_candidate_plausibility_filters_fragments passed")


def test_skip_numeric_and_single_char_fragments():
    """Numeric or one-character tokens should not create broken outputs."""
    text = "Benim 3 kedim ve 5 köpeğim var."
    result = trace_call(lemmatize, text)
    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {type(result).__name__}: {result}")
    if any(tok in {"ağu", "trilyon", "m"} for tok in result):
        raise AssertionError(f"Unexpected broken tokens in output: {result}")
    print("✓ test_skip_numeric_and_single_char_fragments passed")


if __name__ == "__main__":
    test_simple_sentence()
    test_empty_string()
    test_single_word()
    test_multiple_sentences()
    test_with_punctuation()
    test_verb_forms()
    test_mixed_case()
    test_with_numbers()
    test_return_type()
    test_newline_separated_sentences()
    test_turkish_diacritics()
    test_normalize_candidate_mojibake()
    test_candidate_plausibility_filters_fragments()
    test_skip_numeric_and_single_char_fragments()
    print("\n✓ All tests passed!")
