"""Tests for the lemmatizer output normalization module."""

from __future__ import annotations

import sys

from support_lib.Lemmatizer.normalize_output import (
    normalize_lemmatized_output,
    normalize_lemmatized_text,
)


def test_normalize_filters_single_vowels() -> None:
    """Single vowels should be filtered out as artifacts."""
    result = normalize_lemmatized_output(["hello", "i", "world"])
    assert result == ["hello", "world"]


def test_normalize_filters_auxiliary_remnants() -> None:
    """English auxiliary verb remnants should be filtered."""
    result = normalize_lemmatized_output(["i", "run", "be", "test", "a"])
    assert result == ["run", "test"]


def test_normalize_filters_stanza_artifacts() -> None:
    """Turkish stanza pipeline artifacts should be filtered."""
    result = normalize_lemmatized_output(["bugun", "kitap", "oku", "m"])
    # 'bugun' gets normalized to 'bugün' (ü is U+00FC, UTF-8: c3bc)
    assert len(result) == 3
    assert result[1] == "kitap"
    assert result[2] == "oku"
    # Check that first result contains the Turkish ü character (UTF-8 bytes c3bc)
    assert result[0].encode('utf-8') == b'bug\xc3\xbcn'


def test_normalize_keeps_valid_words() -> None:
    """Valid words of 2+ chars should be preserved."""
    result = normalize_lemmatized_output(["run", "quickly", "and", "write", "note"])
    assert result == ["run", "quickly", "and", "write", "note"]


def test_normalize_filters_empty_strings() -> None:
    """Empty strings should be filtered."""
    result = normalize_lemmatized_output(["hello", "", "world", "  "])
    assert result == ["hello", "world"]


def test_normalize_filters_punctuation_only() -> None:
    """Punctuation-only tokens should be filtered."""
    result = normalize_lemmatized_output(["hello", ".", ",", "world"])
    assert result == ["hello", "world"]


def test_normalize_text_string_input() -> None:
    """normalize_lemmatized_text should handle space-separated strings."""
    result = normalize_lemmatized_text("hello i world be test a")
    assert result == "hello world test"


def test_normalize_multilingual_mix() -> None:
    """Mixed English and Turkish should be normalized correctly."""
    result = normalize_lemmatized_output(
        ["run", "quickly", "ve", "bugun", "kitap", "oku", "m"]
    )
    assert len(result) == 6
    assert result[0] == "run"
    assert result[1] == "quickly"
    assert result[2] == "ve"
    # 'bugun' normalized to 'bugün' with ü character
    assert result[3].encode('utf-8') == b'bug\xc3\xbcn'
    assert result[4] == "kitap"
    assert result[5] == "oku"


if __name__ == "__main__":
    print(
        "\n════════════════════════════════════════════════════════════════════════════"
    )
    print("  NORMALIZATION MODULE TESTS")
    print(
        "════════════════════════════════════════════════════════════════════════════\n"
    )

    tests = [
        test_normalize_filters_single_vowels,
        test_normalize_filters_auxiliary_remnants,
        test_normalize_filters_stanza_artifacts,
        test_normalize_keeps_valid_words,
        test_normalize_filters_empty_strings,
        test_normalize_filters_punctuation_only,
        test_normalize_text_string_input,
        test_normalize_multilingual_mix,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            print(f"  ✓ {test_func.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {test_func.__name__}: {e}")
            failed += 1

    print(
        "\n════════════════════════════════════════════════════════════════════════════"
    )
    print(f"  {passed} passed, {failed} failed")
    print(
        "════════════════════════════════════════════════════════════════════════════\n"
    )

    if failed > 0:
        sys.exit(1)
