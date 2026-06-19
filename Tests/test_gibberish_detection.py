# -*- coding: utf-8 -*-
"""Tests for gibberish detection and handling in language detection and lemmatization."""

from Libs.Lemmatizer.LanguageSegmentation.detect_language import detect_text_language
from Libs.Lemmatizer.lemmatize_text import lemmatize_text


def test_detect_language_gibberish_keyboard_mash():
    """Verify that language detection handles keyboard mashes without raising unexpected exceptions."""
    gibberish_inputs = [
        "asdfghjkl",
        "qwertyuiop",
        "zxcvbnm",
        "xzxzxzxzxz",
        "qwert yuiop asdfg hjkl zxcvb nm",
    ]
    for text in gibberish_inputs:
        lang = detect_text_language(text)
        assert isinstance(lang, str)
        assert len(lang) >= 2  # Returns a valid ISO 639-1 language code (e.g., 'en', 'et', etc.)


def test_detect_language_gibberish_special_chars():
    """Verify that language detection falls back to 'gibberish' when input triggers LangDetectException."""
    special_char_gibberish = [
        "!@#$%^&*()_+",
        "1234567890",
        "---___---",
        "!!! ???",
    ]
    for text in special_char_gibberish:
        lang = detect_text_language(text)
        # These are expected to fail language detection and fall back to 'gibberish'
        assert lang == "gibberish"


def test_lemmatize_text_with_gibberish_words():
    """Verify that lemmatize_text preserves unknown/gibberish words as-is, rather than discarding them or crashing."""
    text = "The cats are running quickly asdfghjkl"
    lemmatized = lemmatize_text(text)
    
    # Real words should be lemmatized (e.g., 'cats' -> 'cat', 'are' -> 'be', 'running' -> 'run')
    # and the gibberish word 'asdfghjkl' should be preserved.
    assert "asdfghjkl" in lemmatized
    assert "cat" in lemmatized
    assert "run" in lemmatized


def test_lemmatize_text_pure_gibberish():
    """Verify that lemmatize_text preserves alphabetical keyboard mash words."""
    text = "asdfghjkl qwertyuiop"
    lemmatized = lemmatize_text(text)
    # Alphabetical gibberish should be kept as-is
    assert "asdfghjkl" in lemmatized
    assert "qwertyuiop" in lemmatized


def test_lemmatize_text_special_char_gibberish():
    """Verify that lemmatize_text handles purely non-alphanumeric/punctuation gibberish without crashing."""
    text = "!@#$%^&*()_+"
    lemmatized = lemmatize_text(text)
    assert isinstance(lemmatized, str)

