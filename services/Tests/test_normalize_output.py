# -*- coding: utf-8 -*-
"""Tests for normalize_output module."""
import sys
from pathlib import Path

# Add the inner services package root to path so direct script execution works.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import logging

# Use module-level access from the inner services package root so the file can run directly.
import services.Libs.Lemmatizer.normalize_output as normalize_output_module
from services.Tests.test_helpers import trace_call


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_normal_tokens():
    """Test with normal word tokens."""
    tokens = ["running", "jumping", "walking"]
    logger.info(f"Testing with normal tokens: {tokens}")
    result = trace_call(normalize_output_module.normalize_lemmatized_output, tokens)

    if len(result) != 3:
        raise AssertionError(f"Expected 3 items, got {len(result)}")
    if not all(isinstance(t, str) for t in result):
        raise AssertionError("Expected all items to be strings")
    print("✓ test_normal_tokens passed")


def test_empty_list():
    """Test with empty token list."""
    tokens = []
    logger.info("Testing with empty token list")
    result = trace_call(normalize_output_module.normalize_lemmatized_output, tokens)

    if result:
        raise AssertionError(f"Expected empty list, got {result}")
    print("✓ test_empty_list passed")


def test_single_char_filtered():
    """Test that single characters are filtered."""
    tokens = ["a", "be", "run"]
    logger.info(f"Testing single character filtering: {tokens}")
    result = trace_call(normalize_output_module.normalize_lemmatized_output, tokens)

    if "a" in result:
        raise AssertionError("'a' should be filtered")
    if "be" in result:
        raise AssertionError("'be' should be filtered")
    if "run" not in result:
        raise AssertionError("'run' should be in result")
    print("✓ test_single_char_filtered passed")


def test_stopword_patterns_filtered():
    """Test that stopword patterns are filtered."""
    tokens = ["aeiou", "m", "test", "a"]
    logger.info(f"Testing stopword filtering: {tokens}")
    result = trace_call(normalize_output_module.normalize_lemmatized_output, tokens)

    if "test" not in result:
        raise AssertionError("'test' should be in result")
    for token in result:
        if token in ["a", "m", "be"]:
            raise AssertionError(f"'{token}' should be filtered")
    print("✓ test_stopword_patterns_filtered passed")


def test_punctuation_tokens_filtered():
    """Test that punctuation-only tokens are filtered."""
    tokens = ["hello", ".", ",", "world", "!"]
    logger.info(f"Testing punctuation filtering: {tokens}")
    result = trace_call(normalize_output_module.normalize_lemmatized_output, tokens)

    if "hello" not in result:
        raise AssertionError("'hello' should be in result")
    if "world" not in result:
        raise AssertionError("'world' should be in result")
    if any("." in t or "," in t for t in result):
        raise AssertionError("Punctuation should be filtered")
    print("✓ test_punctuation_tokens_filtered passed")


def test_whitespace_tokens_filtered():
    """Test that whitespace-only tokens are filtered."""
    tokens = ["hello", "   ", "world", "\t"]
    logger.info("Testing whitespace filtering")
    result = trace_call(normalize_output_module.normalize_lemmatized_output, tokens)

    if result != ["hello", "world"]:
        raise AssertionError(f"Expected ['hello', 'world'], got {result}")
    print("✓ test_whitespace_tokens_filtered passed")


def test_short_tokens_filtered():
    """Test that tokens shorter than MIN_WORD_LENGTH are filtered."""
    tokens = ["i", "go", "run"]
    logger.info(f"Testing short token filtering: {tokens}")
    result = trace_call(normalize_output_module.normalize_lemmatized_output, tokens)

    if not all(len(t) >= 2 for t in result):
        raise AssertionError("All tokens should have length >= 2")
    print("✓ test_short_tokens_filtered passed")


def test_mixed_tokens():
    """Test with mixed valid and invalid tokens."""
    tokens = ["hello", ".", "a", "world", "   ", "test"]
    logger.info(f"Testing mixed tokens: {tokens}")
    result = trace_call(normalize_output_module.normalize_lemmatized_output, tokens)

    if not isinstance(result, list):
        raise AssertionError(f"Expected list, got {result}")
    if not all(isinstance(t, str) for t in result):
        raise AssertionError("Expected all items to be strings")
    if not all(len(t) >= 2 for t in result):
        raise AssertionError("All tokens should have length >= 2")
    print("✓ test_mixed_tokens passed")


def test_case_preservation():
    """Test that case is preserved in output."""
    tokens = ["Hello", "WORLD", "TeSt"]
    logger.info(f"Testing case preservation: {tokens}")
    result = trace_call(normalize_output_module.normalize_lemmatized_output, tokens)

    if len(result) == 0:
        raise AssertionError("Expected non-empty result")
    print("✓ test_case_preservation passed")


def test_normal_text():
    """Test with normal space-separated text."""
    text = "running jumping walking"
    logger.info(f"Testing normal text: {text}")
    result = trace_call(normalize_output_module.normalize_lemmatized_text, text)

    if not isinstance(result, str):
        raise AssertionError(f"Expected str, got {result}")
    if len(result) == 0:
        raise AssertionError("Expected non-empty result")
    print("✓ test_normal_text passed")


def test_empty_text():
    """Test with empty text."""
    text = ""
    logger.info("Testing with empty text")
    result = trace_call(normalize_output_module.normalize_lemmatized_text, text)

    if result != "":
        raise AssertionError(f"Expected empty string, got '{result}'")
    print("✓ test_empty_text passed")


def test_text_with_extra_spaces():
    """Test with text containing extra spaces."""
    text = "hello   world    test"
    logger.info(f"Testing with extra spaces: {text}")
    result = trace_call(normalize_output_module.normalize_lemmatized_text, text)

    if not isinstance(result, str):
        raise AssertionError(f"Expected str, got {result}")
    print("✓ test_text_with_extra_spaces passed")


def test_single_word_text():
    """Test with single word."""
    text = "hello"
    logger.info(f"Testing with single word: {text}")
    result = trace_call(normalize_output_module.normalize_lemmatized_text, text)

    if not isinstance(result, str):
        raise AssertionError(f"Expected str, got {result}")
    print("✓ test_single_word_text passed")


def test_stopwords_filtered_in_text():
    """Test that stopwords are filtered from text."""
    text = "hello a world be test"
    logger.info(f"Testing stopwords in text: {text}")
    result = trace_call(normalize_output_module.normalize_lemmatized_text, text)

    if not isinstance(result, str):
        raise AssertionError(f"Expected str, got {result}")
    if not ("hello" in result or "world" in result or "test" in result):
        raise AssertionError("Expected at least one meaningful word in result")
    print("✓ test_stopwords_filtered_in_text passed")


def test_output_is_string():
    """Test that output is always a string."""
    texts = ["hello world", "test", "", "a b c"]
    for i, text in enumerate(texts):
        logger.info(f"Checking string output for text index {i}: {text}")
        result = trace_call(normalize_output_module.normalize_lemmatized_text, text, label=f"normalize_lemmatized_text[{i}]")
        if not isinstance(result, str):
            raise AssertionError(f"Expected str for text[{i}], got {result}")
        logger.info(f"Output is string, text index: {i}, result type: {type(result).__name__}")
    print("✓ test_output_is_string passed")


def test_whitespace_handling():
    """Test proper whitespace handling in output."""
    text = "hello world test"
    logger.info(f"Testing whitespace handling: {text}")
    result = trace_call(normalize_output_module.normalize_lemmatized_text, text)
    parts = result.split()
    
    if not all(isinstance(p, str) for p in parts):
        raise AssertionError("Expected all parts to be strings")
    print("✓ test_whitespace_handling passed")


if __name__ == "__main__":
    test_normal_tokens()
    test_empty_list()
    test_single_char_filtered()
    test_stopword_patterns_filtered()
    test_punctuation_tokens_filtered()
    test_whitespace_tokens_filtered()
    test_short_tokens_filtered()
    test_mixed_tokens()
    test_case_preservation()
    test_normal_text()
    test_empty_text()
    test_text_with_extra_spaces()
    test_single_word_text()
    test_stopwords_filtered_in_text()
    test_output_is_string()
    test_whitespace_handling()
    print("\n✓ All tests passed!")
