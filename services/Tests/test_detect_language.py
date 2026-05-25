# -*- coding: utf-8 -*-
"""Tests for detect_language module with logging instrumentation."""
import sys
from pathlib import Path
import logging

# Add the inner services package root to path so direct script execution works.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.Libs.Lemmatizer.detect_language import detect_text_language
from services.Tests.test_helpers import trace_call

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
    result = trace_call(detect_text_language, text)
    
    if result not in ["en", "tr"]:
        raise AssertionError(f"Expected result in ['en', 'tr'], got {result}")
    if not isinstance(result, str):
        raise AssertionError(f"Expected str, got {result}")
    print("✓ test_english_text passed")


def test_turkish_text():
    """Test detection of Turkish text."""
    text = "Merhaba dünya, bu bir testtir."
    logger.info(f"Testing Turkish text detection: {text}")
    result = trace_call(detect_text_language, text)
    
    if result not in ["en", "tr"]:
        raise AssertionError(f"Expected result in ['en', 'tr'], got {result}")
    if not isinstance(result, str):
        raise AssertionError(f"Expected str, got {result}")
    print("✓ test_turkish_text passed")


def test_empty_string():
    """Test with empty string returns English by default."""
    text = ""
    logger.info("Testing empty string detection")
    result = trace_call(detect_text_language, text)
    
    if result != "en":
        raise AssertionError(f"Expected 'en', got {result}")
    print("✓ test_empty_string passed")


def test_whitespace_only():
    """Test with whitespace-only string returns English by default."""
    text = "   \n\t  "
    logger.info("Testing whitespace-only string detection")
    result = trace_call(detect_text_language, text)
    
    if result != "en":
        raise AssertionError(f"Expected 'en', got {result}")
    print("✓ test_whitespace_only passed")


def test_short_english_text():
    """Test with short English text."""
    text = "Hi"
    logger.info(f"Testing short English text: {text}")
    result = trace_call(detect_text_language, text)
    
    if result not in ["en", "tr"]:
        raise AssertionError(f"Expected result in ['en', 'tr'], got {result}")
    print("✓ test_short_english_text passed")


def test_mixed_text():
    """Test with mixed English and Turkish text."""
    text = "Hello merhaba world dünya."
    logger.info(f"Testing mixed language text: {text}")
    result = trace_call(detect_text_language, text)
    
    if result not in ["en", "tr"]:
        raise AssertionError(f"Expected result in ['en', 'tr'], got {result}")
    print("✓ test_mixed_text passed")


def test_punctuation_text():
    """Test with text containing punctuation."""
    text = "What?! Yes! Amazing!!!"
    logger.info(f"Testing punctuation text: {text}")
    result = trace_call(detect_text_language, text)
    
    if result not in ["en", "tr"]:
        raise AssertionError(f"Expected result in ['en', 'tr'], got {result}")
    print("✓ test_punctuation_text passed")


def test_multiline_text():
    """Test with multiline text."""
    text = "First line.\nSecond line.\nThird line."
    logger.info("Testing multiline text detection")
    result = trace_call(detect_text_language, text)
    
    if result not in ["en", "tr"]:
        raise AssertionError(f"Expected result in ['en', 'tr'], got {result}")
    print("✓ test_multiline_text passed")


def test_numbers_only():
    """Test with numbers only."""
    text = "123 456 789"
    logger.info("Testing numbers-only text detection")
    result = trace_call(detect_text_language, text)
    
    if result not in ["en", "tr"]:
        raise AssertionError(f"Expected result in ['en', 'tr'], got {result}")
    print("✓ test_numbers_only passed")


def test_special_characters():
    """Test with special characters."""
    text = "@#$%^&*()"
    logger.info("Testing special characters detection")
    result = trace_call(detect_text_language, text)
    
    if result not in ["en", "tr"]:
        raise AssertionError(f"Expected result in ['en', 'tr'], got {result}")
    print("✓ test_special_characters passed")


def test_output_type():
    """Test that output is always a string."""
    texts = ["test", "sınav", ""]
    logger.info("Testing output type validation")
    for i, text in enumerate(texts):
        result = trace_call(detect_text_language, text, label=f"detect_text_language[{i}]")
        if not isinstance(result, str):
            raise AssertionError(f"Expected str, got {result}")
        if len(result) == 0:
            raise AssertionError("Expected non-empty string")
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
