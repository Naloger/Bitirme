# -*- coding: utf-8 -*-
"""Tests for lemmatize_english module."""
import sys
from pathlib import Path
import logging

# Add the inner services package root to path so direct script execution works.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.Libs.Lemmatizer.lemmatize_english import lemmatize_english_text
from services.Tests.test_helpers import trace_call


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_simple_sentence():
    """Test lemmatization of simple English sentence."""
    text = "The cats are running quickly."
    logger.info(f"Testing with text: {text}")
    result = trace_call(lemmatize_english_text, text)

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
    logger.info("Testing with empty string")
    result = trace_call(lemmatize_english_text, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    if result:
        raise AssertionError(f"Expected empty list, got {result}")
    print("✓ test_empty_string passed")


def test_single_word():
    """Test with single word."""
    text = "running"
    logger.info(f"Testing with single word: {text}")
    result = trace_call(lemmatize_english_text, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_single_word passed")


def test_multiple_sentences():
    """Test with multiple sentences."""
    text = "I am running. You are walking. They are jumping."
    logger.info(f"Testing with multiple sentences: {text}")
    result = trace_call(lemmatize_english_text, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    if len(result) < 1:
        raise AssertionError(f"Expected at least 1 item, got {len(result)}")
    print("✓ test_multiple_sentences passed")


def test_with_punctuation():
    """Test text with various punctuation marks."""
    text = "What are you doing? I'm running, jumping, and walking!"
    logger.info(f"Testing with punctuation: {text}")
    result = trace_call(lemmatize_english_text, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_with_punctuation passed")


def test_verb_forms():
    """Test lemmatization of various verb forms."""
    text = "runs running walked walks walking."
    logger.info(f"Testing verb forms: {text}")
    result = trace_call(lemmatize_english_text, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_verb_forms passed")


def test_mixed_case():
    """Test with mixed case text."""
    text = "RUNNING fast Running slow running faster."
    logger.info(f"Testing mixed case: {text}")
    result = trace_call(lemmatize_english_text, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_mixed_case passed")


def test_with_numbers():
    """Test text containing numbers."""
    text = "I have 3 cats and 5 dogs."
    logger.info(f"Testing with numbers: {text}")
    result = trace_call(lemmatize_english_text, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_with_numbers passed")


def test_return_type():
    """Test that return type is always list of strings."""
    texts = ["hello world", "test", "", "The quick brown fox"]
    for i, text in enumerate(texts):
        logger.info(f"Checking return type for text index {i}: {text}")
        result = trace_call(lemmatize_english_text, text, label=f"lemmatize_english_text[{i}]")
        if not isinstance(result, list):
            raise AssertionError(f"Expected list for text[{i}], got {result}")
        if not all(isinstance(item, str) for item in result):
            raise AssertionError(f"Expected all items to be strings for text[{i}]")
        logger.info(f"Return type valid for text index {i}, result length: {len(result)}")
    print("✓ test_return_type passed")


def test_newline_separated_sentences():
    """Test with newline-separated sentences."""
    text = "First sentence.\nSecond sentence.\nThird sentence."
    logger.info("Testing newline-separated sentences")
    result = trace_call(lemmatize_english_text, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_newline_separated_sentences passed")


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
    print("\n✓ All tests passed!")
