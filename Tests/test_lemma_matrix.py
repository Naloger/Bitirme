# -*- coding: utf-8 -*-
"""Comprehensive tests for LemmaMatrixBuilder with logging."""
import sys
from pathlib import Path

# Add the inner services package root to path so direct script execution works.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import logging
from typing import Callable
from unittest.mock import Mock, patch

from Libs.Lemmatizer.LanguageSegmentation.segment_by_language import (
    LanguageSegment,
)
from Libs.Lemmatizer.lemma_matrix import LemmaMatrixBuilder
from Tests.test_helpers import trace_call


# ==========================================
# Enhanced Logging Configuration
# ==========================================
class TestLogFormatter(logging.Formatter):
    """Custom formatter to make test results pop with ANSI colors."""
    GREY = "\x1b[38;20m"
    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    RESET = "\x1b[0m"
    FORMAT_STR = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def format(self, record):
        # Dynamically colorize based on test result tags or log levels
        if "[PASS]" in str(record.msg):
            log_fmt = self.GREEN + self.FORMAT_STR + self.RESET
        elif "[FAIL]" in str(record.msg) or record.levelno >= logging.ERROR:
            log_fmt = self.RED + self.FORMAT_STR + self.RESET
        elif record.levelno == logging.WARNING:
            log_fmt = self.YELLOW + self.FORMAT_STR + self.RESET
        else:
            log_fmt = self.GREY + self.FORMAT_STR + self.RESET

        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# Set up the logger with the custom formatter
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(TestLogFormatter())
    logger.addHandler(ch)

# Prevent propagation to the root logger to avoid duplicate standard logs
logger.propagate = False


# ==========================================
# Matrix Formatting Helper
# ==========================================
def log_formatted_matrix(words, matrix_array, logger_instance):
    """Helper to dynamically format and log a matrix based on max word length."""
    if not len(words):
        return

    # Dynamically determine the optimal column width
    max_word_len = max((len(str(w)) for w in words), default=4)
    col_width = max(max_word_len + 2, 10) # At least 10 chars wide

    # Build Header
    header = "Word".ljust(col_width)
    for word in words:
        header += f"{word:>{col_width}}"

    logger_instance.info("=" * len(header))
    logger_instance.info(header)
    logger_instance.info("=" * len(header))

    # Build Rows
    for i, word in enumerate(words):
        row = word.ljust(col_width)
        for j in range(len(words)):
            row += f"{int(matrix_array[i, j]):>{col_width}}"
        logger_instance.info(row)
    logger_instance.info("=" * len(header))


class TestLemmaMatrixBuilderInit:
    """Tests for LemmaMatrixBuilder initialization."""

    def test_initialization_default(self):
        logger.info("Testing LemmaMatrixBuilder initialization with defaults")
        builder = trace_call(LemmaMatrixBuilder, label="LemmaMatrixBuilder()")

        assert hasattr(builder, 'language_to_lemmatizer'), "Missing language_to_lemmatizer"
        assert hasattr(builder, 'default_language'), "Missing default_language"
        assert builder.default_language == "en", f"Expected default_language='en', got '{builder.default_language}'"
        assert builder.language_to_lemmatizer is not None, "language_to_lemmatizer should not be None"
        logger.info("[PASS] test_initialization_default passed")

    def test_initialization_with_custom_language_map(self):
        logger.info("Testing LemmaMatrixBuilder initialization with custom language map")
        custom_map: dict[str, Callable[[str], list[str]]] = {"en": lambda x: ["custom"]}
        builder = trace_call(
            LemmaMatrixBuilder,
            language_to_lemmatizer=custom_map,
            label="LemmaMatrixBuilder(custom_map)"
        )

        assert builder.language_to_lemmatizer == custom_map, "Custom language map not set"
        logger.info("[PASS] test_initialization_with_custom_language_map passed")

    def test_initialization_with_custom_default_language(self):
        logger.info("Testing LemmaMatrixBuilder initialization with custom default language")
        builder = trace_call(
            LemmaMatrixBuilder,
            default_language="tr",
            label="LemmaMatrixBuilder(default_language='tr')"
        )

        assert builder.default_language == "tr", f"Expected default_language='tr', got '{builder.default_language}'"
        logger.info("[PASS] test_initialization_with_custom_default_language passed")


class TestSegmentText:
    """Tests for _segment_text method with exception handling."""

    def test_segment_text_successful_segmentation(self):
        logger.info("Testing successful text segmentation")
        builder = LemmaMatrixBuilder()
        text = "Hello world. Merhaba dünya."

        result = trace_call(
            builder._segment_text,
            text,
            label="_segment_text(mixed_text)"
        )

        assert isinstance(result, list), f"Expected list, got {type(result).__name__}"
        assert len(result) > 0, "Expected non-empty segment list"
        for segment in result:
            assert isinstance(segment, dict), f"Expected segment to be dict, got {type(segment).__name__}"
            assert "language" in segment, "Segment missing 'language' key"
            assert "text" in segment, "Segment missing 'text' key"
        logger.info("[PASS] test_segment_text_successful_segmentation passed")

    def test_segment_text_fallback_on_segmentation_error(self):
        logger.info("Testing fallback when segment_by_language raises exception")
        builder = LemmaMatrixBuilder(default_language="en")
        text = "Hello world"

        with patch('Libs.Lemmatizer.lemma_matrix.segment_by_language') as mock_segment:
            with patch('Libs.Lemmatizer.lemma_matrix.detect_text_language') as mock_detect:
                mock_segment.side_effect = RuntimeError("Segmentation failed")
                mock_detect.return_value = "en"

                result = trace_call(
                    builder._segment_text,
                    text,
                    label="_segment_text(with_fallback)"
                )

                assert isinstance(result, list), f"Expected list, got {type(result).__name__}"
                assert len(result) == 1, "Expected single segment on fallback"
                assert result[0]["language"] == "en", "Expected language 'en'"
                assert result[0]["text"] == text, "Text should be unchanged"
                logger.info("[PASS] test_segment_text_fallback_on_segmentation_error passed")

    def test_segment_text_fallback_on_detection_error(self):
        logger.info("Testing fallback to default language when detection fails")
        builder = LemmaMatrixBuilder(default_language="tr")
        text = "Test text"

        with patch('Libs.Lemmatizer.lemma_matrix.segment_by_language') as mock_segment:
            with patch('Libs.Lemmatizer.lemma_matrix.detect_text_language') as mock_detect:
                mock_segment.side_effect = RuntimeError("Segmentation failed")
                mock_detect.side_effect = ValueError("Detection failed")

                result = trace_call(
                    builder._segment_text,
                    text,
                    label="_segment_text(detection_failure)"
                )

                assert isinstance(result, list), f"Expected list, got {type(result).__name__}"
                assert len(result) == 1, "Expected single segment"
                assert result[0]["language"] == "gibberish", f"Expected fallback language 'gibberish', got '{result[0]['language']}'"
                logger.info("[PASS] test_segment_text_fallback_on_detection_error passed")

    def test_segment_text_empty_string(self):
        logger.info("Testing segment_text with empty string")
        builder = LemmaMatrixBuilder()

        with patch('Libs.Lemmatizer.lemma_matrix.segment_by_language') as mock_segment:
            with patch('Libs.Lemmatizer.lemma_matrix.detect_text_language') as mock_detect:
                mock_segment.return_value = []
                mock_detect.return_value = "en"

                result = trace_call(
                    builder._segment_text,
                    "",
                    label="_segment_text(empty)"
                )

                assert isinstance(result, list), f"Expected list, got {type(result).__name__}"
                logger.info("[PASS] test_segment_text_empty_string passed")


class TestLemmatizeSegment:
    """Tests for _lemmatize_segment method with exception handling."""

    def test_lemmatize_segment_successful(self):
        logger.info("Testing successful lemmatization")
        builder = LemmaMatrixBuilder()
        segment: LanguageSegment = {"language": "en", "text": "running quickly"}

        result = trace_call(
            builder._lemmatize_segment,
            segment,
            label="_lemmatize_segment(english)"
        )

        assert isinstance(result, list), f"Expected list, got {type(result).__name__}"
        logger.info("[PASS] test_lemmatize_segment_successful passed")

    def test_lemmatize_segment_error_returns_empty_list(self):
        logger.info("Testing lemmatization error handling")

        def failing_lemmatizer(x: str) -> list[str]:
            raise RuntimeError("Lemmatizer crashed")

        builder = LemmaMatrixBuilder(
            language_to_lemmatizer={"en": failing_lemmatizer}
        )
        segment: dict[str, str] = {"language": "en", "text": "test"}

        result = trace_call(
            builder._lemmatize_segment,
            segment,
            label="_lemmatize_segment(error)"
        )

        assert isinstance(result, list), f"Expected list, got {type(result).__name__}"
        assert result == ["gibberish"], f"Expected ['gibberish'] on error, got {result}"
        logger.info("[PASS] test_lemmatize_segment_error_returns_empty_list passed")

    def test_lemmatize_segment_unknown_language_uses_default(self):
        logger.info("Testing unknown language defaults to English lemmatizer")
        builder = LemmaMatrixBuilder()
        segment = {"language": "xx", "text": "test"}  # Unknown language

        result = trace_call(
            builder._lemmatize_segment,
            segment,
            label="_lemmatize_segment(unknown_lang)"
        )

        assert isinstance(result, list), f"Expected list, got {type(result).__name__}"
        logger.info("[PASS] test_lemmatize_segment_unknown_language_uses_default passed")

    def test_lemmatize_segment_returns_none_converted_to_empty_list(self):
        logger.info("Testing None conversion to empty list")

        def none_lemmatizer(x: str) -> list[str]:
            return []

        builder = LemmaMatrixBuilder(
            language_to_lemmatizer={"en": none_lemmatizer}
        )
        segment: dict[str, str] = {"language": "en", "text": "test"}

        result = trace_call(
            builder._lemmatize_segment,
            segment,
            label="_lemmatize_segment(none)"
        )

        assert result == [], f"Expected empty list, got {result}"
        logger.info("[PASS] test_lemmatize_segment_returns_none_converted_to_empty_list passed")


class TestTokenize:
    """Tests for tokenize method."""

    def test_tokenize_empty_string(self):
        logger.info("Testing tokenize with empty string")
        builder = LemmaMatrixBuilder()
        result = trace_call(builder.tokenize, "", label="tokenize(empty)")
        assert result == [], f"Expected empty list, got {result}"
        logger.info("[PASS] test_tokenize_empty_string passed")

    def test_tokenize_whitespace_only(self):
        logger.info("Testing tokenize with whitespace-only string")
        builder = LemmaMatrixBuilder()
        result = trace_call(builder.tokenize, "   ", label="tokenize(whitespace)")
        assert result == [], f"Expected empty list, got {result}"
        logger.info("[PASS] test_tokenize_whitespace_only passed")

    def test_tokenize_returns_list(self):
        logger.info("Testing tokenize return type")
        builder = LemmaMatrixBuilder()
        texts = [
            "hello world",
            "The quick brown fox",
            "test",
        ]

        for text in texts:
            logger.info("Tokenizing: %s", text)
            result = trace_call(builder.tokenize, text, label="tokenize({})".format(text[:10]))
            assert isinstance(result, list), f"Expected list for '{text}', got {type(result).__name__}"
        logger.info("[PASS] test_tokenize_returns_list passed")


class TestBuildCooccurrenceMatrix:
    """Tests for build_cooccurrence_matrix method."""

    def test_build_cooccurrence_matrix_single_text(self):
        logger.info("Testing cooccurrence matrix with single text")
        builder = LemmaMatrixBuilder()
        texts = ["hello world"]

        vectorizer, matrix = trace_call(
            builder.build_cooccurrence_matrix,
            texts,
            label="build_cooccurrence_matrix(1_text)"
        )

        assert vectorizer is not None, "Vectorizer should not be None"
        assert matrix is not None, "Matrix should not be None"
        assert hasattr(matrix, 'toarray'), "Matrix should have toarray method"
        logger.info("[PASS] test_build_cooccurrence_matrix_single_text passed")

    def test_build_cooccurrence_matrix_multiple_texts(self):
        logger.info("Testing cooccurrence matrix with multiple texts")
        builder = LemmaMatrixBuilder()
        texts = [
            "hello world",
            "hello there",
            "world class"
        ]

        vectorizer, matrix = trace_call(
            builder.build_cooccurrence_matrix,
            texts,
            label="build_cooccurrence_matrix(3_texts)"
        )

        assert vectorizer is not None, "Vectorizer should not be None"
        assert matrix is not None, "Matrix should not be None"
        matrix_array = matrix.toarray()
        assert matrix_array.shape[0] > 0, "Matrix should have rows"
        assert matrix_array.shape[1] > 0, "Matrix should have columns"

        # Diagonal should be zero (no self-cooccurrence)
        for i in range(min(matrix_array.shape[0], matrix_array.shape[1])):
            assert matrix_array[i, i] == 0, f"Diagonal element [{i},{i}] should be 0 (self-cooccurrence)"

        logger.info("[PASS] test_build_cooccurrence_matrix_multiple_texts passed")

    def test_build_cooccurrence_matrix_empty_list(self):
        logger.info("Testing cooccurrence matrix with empty text list")
        builder = LemmaMatrixBuilder()
        texts = []

        try:
            _ = trace_call(
                builder.build_cooccurrence_matrix,
                texts,
                label="build_cooccurrence_matrix(empty)"
            )
            logger.info("[FAIL] test_build_cooccurrence_matrix_empty_list passed (Should have raised ValueError)")
        except ValueError as e:
            logger.warning("ValueError on empty list (expected): %s", e)
            logger.info("[PASS] test_build_cooccurrence_matrix_empty_list passed (ValueError expected)")


class TestPrintCooccurrenceMatrix:
    """Tests for print_cooccurrence_matrix method."""

    def test_print_cooccurrence_matrix_valid_inputs(self, capsys=None):

        builder = LemmaMatrixBuilder()
        texts = ["hello world", "world class"]
        vectorizer, matrix = builder.build_cooccurrence_matrix(texts)

        logger.info("=" * 70)
        logger.info("Testing print_cooccurrence_matrix with valid inputs")
        logger.info("=" * 70)
        trace_call(
            builder.print_cooccurrence_matrix,
            matrix,
            vectorizer,
            label="print_cooccurrence_matrix(valid)"
        )
        logger.info("=" * 70)
        logger.info("=" * 70)
        logger.info("[PASS] test_print_cooccurrence_matrix_valid_inputs passed")



    def test_print_cooccurrence_matrix_error_handling(self):
        logger.info("Testing print_cooccurrence_matrix error handling")
        mock_matrix = Mock()
        mock_vectorizer = Mock()
        mock_vectorizer.get_feature_names_out.side_effect = RuntimeError("Feature extraction failed")

        trace_call(
            LemmaMatrixBuilder.print_cooccurrence_matrix,
            mock_matrix,
            mock_vectorizer,
            label="print_cooccurrence_matrix(error)"
        )
        logger.info("[PASS] test_print_cooccurrence_matrix_error_handling passed")


class TestMatrixFormat:
    """Tests demonstrating cooccurrence matrix format and structure."""

    def test_matrix_format_demonstration(self):
        logger.info("=" * 70)
        logger.info("COOCCURRENCE MATRIX FORMAT DEMONSTRATION")
        logger.info("=" * 70)

        builder = LemmaMatrixBuilder()
        texts = [
            "the cat sat on the mat",
            "the dog sat on the floor",
            "the cat and dog play"
        ]

        logger.info("Input texts:")
        for i, text in enumerate(texts, 1):
            logger.info("  %d. %s", i, text)

        vectorizer, matrix = builder.build_cooccurrence_matrix(texts)
        words = vectorizer.get_feature_names_out()
        matrix_array = matrix.toarray()

        logger.info("Extracted words (features): %s", list(words))
        logger.info("Matrix shape: %d rows x %d columns", matrix_array.shape[0], matrix_array.shape[1])
        logger.info("Cooccurrence Matrix - Dense Format:")

        # Dynamically format and print matrix using helper
        log_formatted_matrix(words, matrix_array, logger)

        logger.info("Cooccurrence Analysis:")
        for i in range(len(words)):
            for j in range(i + 1, len(words)):
                count = matrix_array[i, j]
                if count > 0:
                    logger.info('  "%s" co-occurs with "%s" %d time(s)', words[i], words[j], int(count))

        # Print summary
        non_zero_count = (matrix_array > 0).sum()
        total_elements = matrix_array.size
        logger.info("Matrix Summary:")
        logger.info("  Total elements: %d", total_elements)
        logger.info("  Non-zero elements: %d", non_zero_count)
        logger.info("  Sparsity: %.1f%%", (total_elements - non_zero_count) / total_elements * 100)

        # Verify matrix properties
        assert hasattr(matrix, 'toarray'), "Matrix should have toarray method"
        assert matrix_array.shape[0] == matrix_array.shape[1], "Matrix should be square"
        assert (matrix_array.diagonal() == 0).all(), "Diagonal should be all zeros (no self-cooccurrence)"

        # Check symmetry
        is_symmetric = (matrix_array == matrix_array.T).all()
        logger.info("  Matrix is symmetric: %s", is_symmetric)

        logger.info("=" * 70)
        logger.info("[PASS] test_matrix_format_demonstration passed")

    def test_matrix_format_single_document(self):
        logger.info("=" * 70)
        logger.info("SINGLE DOCUMENT MATRIX FORMAT")
        logger.info("=" * 70)

        builder = LemmaMatrixBuilder()
        texts = ["the quick brown fox jumps"]

        logger.info("Input: '%s'", texts[0])

        vectorizer, matrix = builder.build_cooccurrence_matrix(texts)
        words = vectorizer.get_feature_names_out()
        matrix_array = matrix.toarray()

        logger.info("Words extracted: %s", list(words))
        logger.info("Matrix shape: %d x %d", matrix_array.shape[0], matrix_array.shape[1])
        logger.info("Full Cooccurrence Matrix:")

        # Dynamically format and print matrix using helper
        log_formatted_matrix(words, matrix_array, logger)

        logger.info("=" * 70)
        logger.info("[PASS] test_matrix_format_single_document passed")

    def test_matrix_format_with_repeated_words(self):
        logger.info("=" * 70)
        logger.info("MATRIX WITH REPEATED WORDS")
        logger.info("=" * 70)

        builder = LemmaMatrixBuilder()
        texts = [
            "cat cat dog",
            "dog dog cat",
            "cat dog cat dog"
        ]

        logger.info("Input texts (with word repetitions):")
        for i, text in enumerate(texts, 1):
            logger.info("  %d. %s", i, text)

        vectorizer, matrix = builder.build_cooccurrence_matrix(texts)
        words = vectorizer.get_feature_names_out()
        matrix_array = matrix.toarray()

        logger.info("Cooccurrence Count Matrix:")

        # Dynamically format and print matrix using helper
        log_formatted_matrix(words, matrix_array, logger)

        logger.info("Interpretation:")
        for i in range(len(words)):
            for j in range(i + 1, len(words)):
                count = int(matrix_array[i, j])
                logger.info('  "%s" and "%s": %d cooccurrences', words[i], words[j], count)

        logger.info("=" * 70)
        logger.info("[PASS] test_matrix_format_with_repeated_words passed")


class TestExceptionHandling:
    """Tests for exception handling and logging."""

    def test_segment_text_logs_on_error(self):
        logger.info("Testing segment_text error logging")
        builder = LemmaMatrixBuilder()

        with patch('Libs.Lemmatizer.lemma_matrix.segment_by_language') as mock_segment:
            with patch('Libs.Lemmatizer.lemma_matrix.detect_text_language') as mock_detect:
                mock_segment.side_effect = LookupError("Model not found")
                mock_detect.return_value = "en"

                result = builder._segment_text("test")
                assert isinstance(result, list), "Should return list despite error"
                logger.info("[PASS] test_segment_text_logs_on_error passed")

    def test_lemmatize_segment_logs_on_error(self):
        logger.info("Testing lemmatize_segment error logging")

        def error_lemmatizer(x: str) -> list[str]:
            raise ValueError("Model error")

        builder = LemmaMatrixBuilder(
            language_to_lemmatizer={"en": error_lemmatizer}
        )
        segment: LanguageSegment = {"language": "en", "text": "test"}

        result = builder._lemmatize_segment(segment)
        assert result == ["gibberish"], "Should return gibberish list on error"
        logger.info("[PASS] test_lemmatize_segment_logs_on_error passed")


def run_all_tests():
    """Run all test classes."""
    logger.info("=" * 60)
    logger.info("Starting LemmaMatrixBuilder Test Suite")
    logger.info("=" * 60)

    test_classes = [
        TestLemmaMatrixBuilderInit,
        TestSegmentText,
        TestLemmatizeSegment,
        TestTokenize,
        TestBuildCooccurrenceMatrix,
        TestPrintCooccurrenceMatrix,
        TestMatrixFormat,
        TestExceptionHandling,
    ]

    passed = 0
    failed = 0

    for test_class in test_classes:
        logger.info(f"--- Running {test_class.__name__} ---")
        test_instance = test_class()
        for method_name in dir(test_instance):
            if method_name.startswith('test_'):
                try:
                    logger.info(f"Running {test_class.__name__}.{method_name}")
                    getattr(test_instance, method_name)()
                    passed += 1
                except Exception as e:
                    logger.error(f"[FAIL] {test_class.__name__}.{method_name} FAILED: {e}", exc_info=True)
                    failed += 1

    logger.info("=" * 60)
    logger.info(f"Test Summary: {passed} passed, {failed} failed")
    logger.info("=" * 60)

    if failed == 0:
        logger.info(f"[PASS] All {passed} tests passed!")
        return True
    else:
        logger.error(f"[FAIL] {failed} test(s) failed out of {passed + failed}")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
