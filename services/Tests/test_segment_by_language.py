# -*- coding: utf-8 -*-
"""Tests for segment_by_language module."""
import logging as logging
import sys
from pathlib import Path

# Add the inner services package root to path so direct script execution works.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.Libs.Lemmatizer.LanguageSegmentation.segment_by_language import (
    mark_text_by_language,
    segment_by_language,
)
from services.Tests.test_helpers import trace_call

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _assert_language_code(value: object) -> None:
    if not isinstance(value, str):
        raise AssertionError(f"Expected language to be str, got {type(value)}")
    if not value.strip():
        raise AssertionError("Expected non-empty language code")


def test_english_text():
    """Test segmentation of English text."""
    text = "Hello world. This is English."
    logger.info(f"Testing English text segmentation: {text}")
    result = trace_call(segment_by_language, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    if len(result) == 0:
        raise AssertionError("Expected non-empty list")
    for segment in result:
        if "language" not in segment:
            raise AssertionError("Missing 'language' in segment")
        if "text" not in segment:
            raise AssertionError("Missing 'text' in segment")
        _assert_language_code(segment["language"])
    print("✓ test_english_text passed")


def test_turkish_text():
    """Test segmentation of Turkish text."""
    text = "Merhaba dünya. Bu Türkçe."
    logger.info(f"Testing Turkish text segmentation: {text}")
    result = trace_call(segment_by_language, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    if len(result) == 0:
        raise AssertionError("Expected non-empty list")
    for segment in result:
        if not isinstance(segment, dict):
            raise AssertionError(f"Expected dict, got {segment}")
    print("✓ test_turkish_text passed")


def test_empty_string():
    """Test with empty string."""
    text = ""
    logger.info("Testing with empty string")
    result = trace_call(segment_by_language, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_empty_string passed")


def test_mixed_language_text():
    """Test with mixed language text."""
    text = "Hello world. Merhaba dünya."
    logger.info(f"Testing mixed language text: {text}")
    result = trace_call(segment_by_language, text)
    languages = [seg["language"] for seg in result]
    logger.info(f"Mixed language segmented, languages: {languages}")

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    if not languages:
        raise AssertionError("Expected at least one language segment")
    for language in languages:
        _assert_language_code(language)
    print("✓ test_mixed_language_text passed")


def test_single_word():
    """Test with single word."""
    text = "hello"
    logger.info(f"Testing with single word: {text}")
    result = trace_call(segment_by_language, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_single_word passed")


def test_punctuation_handling():
    """Test proper punctuation handling."""
    text = "Hello! How are you? I'm fine."
    logger.info(f"Testing punctuation handling: {text}")
    result = trace_call(segment_by_language, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    for segment in result:
        if not isinstance(segment, dict):
            raise AssertionError(f"Expected dict, got {segment}")
    print("✓ test_punctuation_handling passed")


def test_newline_separation():
    """Test text with newlines."""
    text = "First line.\nSecond line.\nThird line."
    logger.info("Testing newline-separated text")
    result = trace_call(segment_by_language, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_newline_separation passed")


def test_multiple_punctuation():
    """Test with multiple consecutive punctuation marks."""
    text = "What?! Really?! Yes!!!"
    logger.info(f"Testing multiple punctuation: {text}")
    result = trace_call(segment_by_language, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_multiple_punctuation passed")


def test_segment_structure():
    """Test that each segment has required structure."""
    text = "Hello. Merhaba."
    logger.info("Testing segment structure validation")
    result = trace_call(segment_by_language, text)
    for i, segment in enumerate(result):
        logger.info(f"Checking structure for segment {i}")
        if not isinstance(segment, dict):
            raise AssertionError(f"Expected dict, got {segment}")
        if "language" not in segment:
            raise AssertionError(f"Missing 'language' in segment {i}")
        if "text" not in segment:
            raise AssertionError(f"Missing 'text' in segment {i}")
        if not isinstance(segment["language"], str):
            raise AssertionError(f"Expected language to be str, got {type(segment['language'])}")
        if not isinstance(segment["text"], str):
            raise AssertionError(f"Expected text to be str, got {type(segment['text'])}")
        logger.info(f"Segment structure valid, segment index: {i}, language: {segment['language']}")
    print("✓ test_segment_structure passed")


def test_english_marking():
    """Test marking of English text."""
    text = "Hello world."
    logger.info(f"Testing English marking: {text}")
    result = trace_call(mark_text_by_language, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    if len(result) == 0:
        raise AssertionError("Expected non-empty list")
    if not all(isinstance(item, str) for item in result):
        raise AssertionError("Expected all items to be strings")
    print("✓ test_english_marking passed")


def test_turkish_marking():
    """Test marking of Turkish text."""
    text = "Merhaba dünya."
    logger.info(f"Testing Turkish marking: {text}")
    result = trace_call(mark_text_by_language, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    if not all(isinstance(item, str) for item in result):
        raise AssertionError("Expected all items to be strings")
    print("✓ test_turkish_marking passed")


def test_mixed_marking():
    """Test marking of mixed language text."""
    text = "Hello. Merhaba."
    logger.info(f"Testing mixed language marking: {text}")
    result = trace_call(mark_text_by_language, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    for line in result:
        if not line.startswith("[") or "] " not in line:
            raise AssertionError(f"Expected '[language] text' format in line: {line}")
    print("✓ test_mixed_marking passed")


def test_empty_string_marking():
    """Test with empty string."""
    text = ""
    logger.info("Testing with empty string")
    result = trace_call(mark_text_by_language, text)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    print("✓ test_empty_string_marking passed")


def test_format_structure():
    """Test that output format is [language] text."""
    text = "Hello world."
    logger.info("Testing format structure")
    result = trace_call(mark_text_by_language, text)
    for i, line in enumerate(result):
        logger.info(f"Checking format for line {i}: {line}")
        if "[" not in line or "]" not in line:
            raise AssertionError(f"Expected '[' and ']' in line: {line}")
        logger.info(f"Format valid: {line}")
    print("✓ test_format_structure passed")


def test_return_type():
    """Test that return type is always list of strings."""
    texts = ["hello", "merhaba", "hello merhaba", ""]
    for i, text in enumerate(texts):
        logger.info(f"Checking return type for text index {i}: {text}")
        result = trace_call(mark_text_by_language, text, label=f"mark_text_by_language[{i}]")
        if not isinstance(result, list):
            raise AssertionError(f"Expected list for text[{i}], got {result}")
        if not all(isinstance(item, str) for item in result):
            raise AssertionError(f"Expected all items to be strings for text[{i}]")
        logger.info(f"Return type valid, text index: {i}, result count: {len(result)}")
    print("✓ test_return_type passed")


if __name__ == "__main__":
    test_english_text()
    test_turkish_text()
    test_empty_string()
    test_mixed_language_text()
    test_single_word()
    test_punctuation_handling()
    test_newline_separation()
    test_multiple_punctuation()
    test_segment_structure()
    test_english_marking()
    test_turkish_marking()
    test_mixed_marking()
    test_empty_string_marking()
    test_format_structure()
    test_return_type()
    print("\n✓ All tests passed!")
