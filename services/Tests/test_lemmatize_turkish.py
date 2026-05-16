# -*- coding: utf-8 -*-
"""Tests for lemmatize_turkish module with logging instrumentation."""
import sys
from pathlib import Path

# Add services directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

try:
    from ..Libs.Lemmatizer.lemmatize_turkish import lemmatize_turkish_text
except ImportError:
    from Libs.Lemmatizer.lemmatize_turkish import lemmatize_turkish_text

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
    result = lemmatize_turkish_text(text)
    logger.info(f"Turkish sentence lemmatized: {result}")
    
    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {type(result)}")
    if len(result) == 0:
        raise AssertionError(f"Expected non-empty list")
    if not all(isinstance(item, str) for item in result):
        raise AssertionError(f"Expected all items to be strings")
    print("✓ test_simple_sentence passed")


def test_empty_string():
    """Test with empty string."""
    text = ""
    logger.info("Testing empty Turkish string")
    result = lemmatize_turkish_text(text)
    logger.info(f"Empty Turkish text handled: {result}")
    
    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {type(result)}")
    if result != []:
        raise AssertionError(f"Expected empty list, got {result}")
    print("✓ test_empty_string passed")


def test_single_word():
    """Test with single word."""
    text = "koşuyor"
    logger.info(f"Testing single Turkish word: {text}")
    result = lemmatize_turkish_text(text)
    logger.info(f"Single Turkish word result: {result}")
    
    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {type(result)}")
    print("✓ test_single_word passed")


def test_multiple_sentences():
    """Test with multiple sentences."""
    text = "Ben koşuyorum. Sen yürüyorsun. Onlar atlıyorlar."
    logger.info(f"Testing multiple Turkish sentences")
    result = lemmatize_turkish_text(text)
    logger.info(f"Multiple Turkish sentences processed: {len(result)} items")
    
    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {type(result)}")
    if len(result) < 1:
        raise AssertionError(f"Expected at least 1 item, got {len(result)}")
    print("✓ test_multiple_sentences passed")


def test_with_punctuation():
    """Test text with various punctuation marks."""
    text = "Ne yapıyorsun? Ben koşuyorum, atlıyorum ve yürüyorum!"
    logger.info(f"Testing Turkish text with punctuation")
    result = lemmatize_turkish_text(text)
    logger.info(f"Turkish punctuation handled: {len(result)} items")
    
    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {type(result)}")
    print("✓ test_with_punctuation passed")


def test_verb_forms():
    """Test lemmatization of various verb forms."""
    text = "koşuyor koşuyorum koştum koşacak."
    logger.info(f"Testing Turkish verb forms")
    result = lemmatize_turkish_text(text)
    logger.info(f"Turkish verb forms lemmatized: {result}")
    
    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {type(result)}")
    print("✓ test_verb_forms passed")


def test_mixed_case():
    """Test with mixed case text."""
    text = "KOŞUYOR hızlı Koşuyor yavaş koşuyor daha hızlı."
    logger.info(f"Testing Turkish mixed case text")
    result = lemmatize_turkish_text(text)
    logger.info(f"Turkish mixed case handled: {result}")
    
    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {type(result)}")
    print("✓ test_mixed_case passed")


def test_with_numbers():
    """Test text containing numbers."""
    text = "Benim 3 kedim ve 5 köpeğim var."
    logger.info(f"Testing Turkish text with numbers")
    result = lemmatize_turkish_text(text)
    logger.info(f"Turkish numbers handled: {result}")
    
    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {type(result)}")
    print("✓ test_with_numbers passed")


def test_return_type():
    """Test that return type is always list of strings."""
    texts = ["merhaba dünya", "sınav", "", "Türk dilinde cümle"]
    logger.info("Testing Turkish return type validation")
    for i, text in enumerate(texts):
        result = lemmatize_turkish_text(text)
        if not isinstance(result, list):
            raise AssertionError(f"Expected list for text[{i}], got {type(result)}")
        if not all(isinstance(item, str) for item in result):
            raise AssertionError(f"Expected all items to be strings for text[{i}]")
        logger.info(f"Turkish return type valid for text[{i}]: {len(result)} items")
    print("✓ test_return_type passed")


def test_newline_separated_sentences():
    """Test with newline-separated sentences."""
    text = "İlk cümle.\nİkinci cümle.\nÜçüncü cümle."
    logger.info("Testing Turkish newline-separated sentences")
    result = lemmatize_turkish_text(text)
    logger.info(f"Turkish newline handling complete: {result}")
    
    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {type(result)}")
    print("✓ test_newline_separated_sentences passed")


def test_turkish_diacritics():
    """Test handling of Turkish diacritics."""
    text = "Türkçe karakterler: ç, ğ, ı, ö, ş, ü"
    logger.info("Testing Turkish diacritics handling")
    result = lemmatize_turkish_text(text)
    logger.info(f"Turkish diacritics handled: {result}")
    
    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {type(result)}")
    print("✓ test_turkish_diacritics passed")


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
    print("\n✓ All tests passed!")
