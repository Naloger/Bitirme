# -*- coding: utf-8 -*-
"""Readable tests for `detect_language` with a small amount of tracing."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Add the inner services package root to path so direct script execution works.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Libs.Lemmatizer.LanguageSegmentation.detect_language import (
    detect_text_language,
)
from Tests.test_helpers import trace_call

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


VALID_LANGUAGE_CASES = [
    ("english", "Hello world, this is a test."),
    ("turkish", "Merhaba dünya, bu bir testtir."),
    ("short_english", "Hi"),
    ("mixed", "Hello merhaba world dünya."),
    ("punctuation", "What?! Yes! Amazing!!!"),
    ("multiline", "First line.\nSecond line.\nThird line."),
    ("numbers_only", "123 456 789"),
    ("special_characters", "@#$%^&*()"),
]

INVALID_INPUT_CASES = [
    ("empty_string", ""),
    ("whitespace_only", "   \n\t  "),
]


def _assert_language_code(result: object) -> None:
    """Ensure the detector returned a usable language code."""
    assert isinstance(result, str), f"Expected str, got {type(result).__name__}: {result!r}"
    assert result.strip(), "Expected a non-empty language code"


def _detect(text: str, *, label: str | None = None) -> str:
    """Run language detection through the trace helper."""
    return trace_call(detect_text_language, text, label=label)


def test_detect_language_returns_code_for_valid_inputs() -> None:
    """Language detection should return a non-empty code for valid input."""
    for case_name, text in VALID_LANGUAGE_CASES:
        logger.info("Testing %s input: %r", case_name, text)
        result = _detect(text, label=f"detect_text_language[{case_name}]")
        _assert_language_code(result)


def test_detect_language_rejects_empty_input() -> None:
    """Blank input should fail clearly instead of returning a fake language code."""
    for case_name, text in INVALID_INPUT_CASES:
        logger.info("Testing %s input: %r", case_name, text)
        try:
            _detect(text, label=f"detect_text_language[{case_name}]")
        except RuntimeError:
            continue
        raise AssertionError(f"Expected RuntimeError for {case_name}")


def test_detect_language_always_returns_string_for_valid_input() -> None:
    """A valid sample should always produce a string result."""
    result = _detect("sınav", label="detect_text_language[type_check]")
    assert isinstance(result, str)
    assert result


if __name__ == "__main__":
    for case_name, text in VALID_LANGUAGE_CASES:
        _assert_language_code(_detect(text, label=f"detect_text_language[{case_name}]"))

    for case_name, text in INVALID_INPUT_CASES:
        try:
            _detect(text, label=f"detect_text_language[{case_name}]")
        except RuntimeError:
            continue
        raise AssertionError(f"Expected RuntimeError for {case_name}")

    _assert_language_code(_detect("sınav", label="detect_text_language[type_check]"))
    print("\n✓ All tests passed!")
