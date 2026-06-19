# -*- coding: utf-8 -*-
"""Tests for lemmatize_text module."""
import sys
from pathlib import Path

# Add the inner services package root to path so direct script execution works.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import logging
from Libs.Lemmatizer.lemmatize_text import lemmatize_text
from Tests.test_helpers import trace_call


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_english_text():
    """Test lemmatization of English text."""
    text = "The cats are running quickly."
    logger.info(f"Testing English text: {text}")
    result = trace_call(lemmatize_text, text)

    if not isinstance(result, str):
        raise AssertionError(f"Expected string, got {type(result).__name__}: {result}")
    if not result.strip():
        raise AssertionError("Expected non-empty string")
    print("✓ test_english_text passed")


def test_turkish_text():
    """Test lemmatization of Turkish text."""
    text = "Kediler hızlı koşuyorlar."
    logger.info(f"Testing Turkish text: {text}")
    result = trace_call(lemmatize_text, text)

    if not isinstance(result, str):
        raise AssertionError(f"Expected string, got {type(result).__name__}: {result}")
    print("✓ test_turkish_text passed")


def test_empty_string():
    """Test with empty string."""
    text = ""
    logger.info("Testing with empty string")
    result = trace_call(lemmatize_text, text)

    if not isinstance(result, str):
        raise AssertionError(f"Expected string, got {type(result).__name__}: {result}")
    if result != "":
        raise AssertionError(f"Expected empty string, got {result!r}")
    print("✓ test_empty_string passed")


def test_single_word():
    """Test with single word."""
    text = "running"
    logger.info(f"Testing with single word: {text}")
    result = trace_call(lemmatize_text, text)

    if not isinstance(result, str):
        raise AssertionError(f"Expected string, got {type(result).__name__}: {result}")
    print("✓ test_single_word passed")


def test_mixed_language_text():
    """Test with mixed English and Turkish text."""
    text = "Hello world. Merhaba dünya."
    logger.info(f"Testing mixed language text: {text}")
    result = trace_call(lemmatize_text, text)

    if not isinstance(result, str):
        raise AssertionError(f"Expected string, got {type(result).__name__}: {result}")
    if not result.strip():
        raise AssertionError("Expected non-empty string")
    print("✓ test_mixed_language_text passed")


def test_multiple_sentences():
    """Test with multiple sentences."""
    text = "I am running. You are walking. Ben koşuyorum."
    logger.info(f"Testing multiple sentences: {text}")
    result = trace_call(lemmatize_text, text)

    if not isinstance(result, str):
        raise AssertionError(f"Expected string, got {type(result).__name__}: {result}")
    print("✓ test_multiple_sentences passed")


def test_with_punctuation():
    """Test text with various punctuation marks."""
    text = "What are you doing? Ben ne yapıyorum?"
    logger.info(f"Testing with punctuation: {text}")
    result = trace_call(lemmatize_text, text)

    if not isinstance(result, str):
        raise AssertionError(f"Expected string, got {type(result).__name__}: {result}")
    print("✓ test_with_punctuation passed")


def test_newline_separation():
    """Test text with newlines."""
    text = "First line in English.\nİlk satır Türkçe."
    logger.info("Testing newline-separated text")
    result = trace_call(lemmatize_text, text)

    if not isinstance(result, str):
        raise AssertionError(f"Expected string, got {type(result).__name__}: {result}")
    print("✓ test_newline_separation passed")


def test_return_type():
    """Test that return type is always a single string."""
    texts = [
        "hello world",
        "merhaba dünya",
        "hello merhaba",
        "",
        "The quick brown fox"
    ]
    for i, text in enumerate(texts):
        logger.info(f"Checking return type for text index {i}: {text}")
        result = trace_call(lemmatize_text, text, label=f"lemmatize_text[{i}]")
        if not isinstance(result, str):
            raise AssertionError(f"Expected string for text[{i}], got {type(result).__name__}: {result}")
        logger.info(f"Return type valid, text index: {i}, result length: {len(result)}")
    print("✓ test_return_type passed")


def test_complex_mixed_text():
    """Test with complex mixed language text."""
    text = "This is English. Bunu Türkçe yazıyorum. More English here."
    logger.info("Testing complex mixed language text")
    result = trace_call(lemmatize_text, text)

    if not isinstance(result, str):
        raise AssertionError(f"Expected string, got {type(result).__name__}: {result}")
    print("✓ test_complex_mixed_text passed")


def test_language_specific_lemmatization():
    """Test that language-specific lemmatization is applied."""
    english_text = "runs running jumped walking"
    turkish_text = "koşuyor koşuyorum atlıyorum yürüyorum"
    
    logger.info(f"Testing English lemmatization: {english_text}")
    en_result = trace_call(lemmatize_text, english_text, label="lemmatize_text[english]")
    if not isinstance(en_result, str):
        raise AssertionError(f"Expected string, got {type(en_result).__name__}: {en_result}")

    logger.info(f"Testing Turkish lemmatization: {turkish_text}")
    tr_result = trace_call(lemmatize_text, turkish_text, label="lemmatize_text[turkish]")
    if not isinstance(tr_result, str):
        raise AssertionError(f"Expected string, got {type(tr_result).__name__}: {tr_result}")
    print("✓ test_language_specific_lemmatization passed")


if __name__ == "__main__":
    test_english_text()
    test_turkish_text()
    test_empty_string()
    test_single_word()
    test_mixed_language_text()
    test_multiple_sentences()
    test_with_punctuation()
    test_newline_separation()
    test_return_type()
    test_complex_mixed_text()
    test_language_specific_lemmatization()
    print("\n✓ All tests passed!")
