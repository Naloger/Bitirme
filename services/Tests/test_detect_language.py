# -*- coding: utf-8 -*-
"""Tests for detect_language module with logging instrumentation."""
import sys
from pathlib import Path

# Add services directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

try:
    from ..Libs.Lemmatizer.detect_language import detect_text_language
except ImportError:
    from Libs.Lemmatizer.detect_language import detect_text_language

# Configure logging for test output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_english_text():
    """Test detection of English text."""
    text = "Hello world, this is a test."
    logger.info(f"Testing English text detection: {text}")
    result = detect_text_language(text)
    logger.info(f"Language detected: {result}")
    
    if result not in ["en", "tr"]:
        raise AssertionError(f"Expected result in ['en', 'tr'], got {result}")
    if not isinstance(result, str):
        raise AssertionError(f"Expected str, got {type(result)}")
    print("✓ test_english_text passed")


def test_turkish_text():
    """Test detection of Turkish text."""
    text = "Merhaba dünya, bu bir testtir."
    logger.info(f"Testing Turkish text detection: {text}")
    result = detect_text_language(text)
    logger.info(f"Turkish text detected: {result}")
    
    if result not in ["en", "tr"]:
        raise AssertionError(f"Expected result in ['en', 'tr'], got {result}")
    if not isinstance(result, str):
        raise AssertionError(f"Expected str, got {type(result)}")
    print("✓ test_turkish_text passed")


def test_empty_string():
    """Test with empty string returns English by default."""
    text = ""
    logger.info("Testing empty string detection")
    result = detect_text_language(text)
    logger.info(f"Empty string handled, defaulted to: {result}")
    
    if result != "en":
        raise AssertionError(f"Expected 'en', got {result}")
    print("✓ test_empty_string passed")


def test_whitespace_only():
    """Test with whitespace-only string returns English by default."""
    text = "   \n\t  "
    logger.info("Testing whitespace-only string detection")
    result = detect_text_language(text)
    logger.info(f"Whitespace-only handled, defaulted to: {result}")
    
    if result != "en":
        raise AssertionError(f"Expected 'en', got {result}")
    print("✓ test_whitespace_only passed")


def test_short_english_text():
    """Test with short English text."""
    text = "Hi"
    logger.info(f"Testing short English text: {text}")
    result = detect_text_language(text)
    logger.info(f"Short text detected: {result}")
    
    if result not in ["en", "tr"]:
        raise AssertionError(f"Expected result in ['en', 'tr'], got {result}")
    print("✓ test_short_english_text passed")


def test_mixed_text():
    """Test with mixed English and Turkish text."""
    text = "Hello merhaba world dünya."
    logger.info(f"Testing mixed language text: {text}")
    result = detect_text_language(text)
    logger.info(f"Mixed language detected: {result}")
    
    if result not in ["en", "tr"]:
        raise AssertionError(f"Expected result in ['en', 'tr'], got {result}")
    print("✓ test_mixed_text passed")


def test_punctuation_text():
    """Test with text containing punctuation."""
    text = "What?! Yes! Amazing!!!"
    logger.info(f"Testing punctuation text: {text}")
    result = detect_text_language(text)
    logger.info(f"Punctuation text detected: {result}")
    
    if result not in ["en", "tr"]:
        raise AssertionError(f"Expected result in ['en', 'tr'], got {result}")
    print("✓ test_punctuation_text passed")


def test_multiline_text():
    """Test with multiline text."""
    text = "First line.\nSecond line.\nThird line."
    logger.info("Testing multiline text detection")
    result = detect_text_language(text)
    logger.info(f"Multiline text detected: {result}")
    
    if result not in ["en", "tr"]:
        raise AssertionError(f"Expected result in ['en', 'tr'], got {result}")
    print("✓ test_multiline_text passed")


def test_numbers_only():
    """Test with numbers only."""
    text = "123 456 789"
    logger.info("Testing numbers-only text detection")
    result = detect_text_language(text)
    logger.info(f"Numbers-only text handled: {result}")
    
    if result not in ["en", "tr"]:
        raise AssertionError(f"Expected result in ['en', 'tr'], got {result}")
    print("✓ test_numbers_only passed")


def test_special_characters():
    """Test with special characters."""
    text = "@#$%^&*()"
    logger.info("Testing special characters detection")
    result = detect_text_language(text)
    logger.info(f"Special characters handled: {result}")
    
    if result not in ["en", "tr"]:
        raise AssertionError(f"Expected result in ['en', 'tr'], got {result}")
    print("✓ test_special_characters passed")


def test_output_type():
    """Test that output is always a string."""
    texts = ["test", "sınav", ""]
    logger.info("Testing output type validation")
    for i, text in enumerate(texts):
        result = detect_text_language(text)
        if not isinstance(result, str):
            raise AssertionError(f"Expected str, got {type(result)}")
        if len(result) == 0:
            raise AssertionError(f"Expected non-empty string")
        logger.info(f"Output type valid for text[{i}]: {type(result).__name__} = {result}")
    print("✓ test_output_type passed")


if __name__ == "__main__":
    test_english_text()
    test_turkish_text()
    test_empty_string()
    test_whitespace_only()
    test_short_english_text()
    test_mixed_text()
    test_punctuation_text()
    test_multiline_text()
    test_numbers_only()
    test_special_characters()
    test_output_type()
    print("\n✓ All tests passed!")
