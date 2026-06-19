import logging

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from Libs.Lemmatizer.lemma_matrix import LemmaMatrixBuilder

# Assuming your class is in a module named 'matrix_builder'
# from matrix_builder import LemmaMatrixBuilder

# --- Configure Logging for Tests ---
# This ensures our test logs have a clear format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - TEST LOGGER - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# --- Mocks & Fixtures ---

class MockVectorizer:
    """Mocks the behavior of scikit-learn's CountVectorizer for testing."""
    def get_feature_names_out(self):
        return np.array(["apple", "banana", "cherry"])

@pytest.fixture
def vectorizer():
    """Provides a fresh MockVectorizer for tests that request it."""
    logger.debug("Fixture 'vectorizer' initializing...")
    return MockVectorizer()

@pytest.fixture
def matrix():
    """Provides a predictable, sparse co-occurrence matrix."""
    print("\n[SETUP] Creating sparse matrix for test...")
    logger.info("Initializing 3x3 mock co-occurrence matrix.")

    #          apple(0)  banana(1)  cherry(2)
    # apple      0         3          1
    # banana     3         0          2
    # cherry     1         2          0
    matrix_data = np.array([
        [0, 3, 1],
        [3, 0, 2],
        [1, 2, 0]
    ])
    return csr_matrix(matrix_data)


# --- Tests ---

def test_extract_matrix_pairs(matrix, vectorizer):
    print("\n" + "="*50)
    print("RUNNING: test_extract_matrix_pairs")
    logger.info("Starting extraction test...")

    # Call the static method
    pairs = LemmaMatrixBuilder.extract_matrix_pairs(matrix, vectorizer)

    logger.info(f"Successfully extracted {len(pairs)} pairs.")
    print(f"[TEST RUN] Raw extracted pairs: {pairs}")

    # 1. Check that we got exactly 3 pairs
    assert len(pairs) == 3

    expected_pairs = [
        {"word1": "apple", "word2": "banana", "weight": 3},
        {"word1": "apple", "word2": "cherry", "weight": 1},
        {"word1": "banana", "word2": "cherry", "weight": 2},
    ]

    pairs.sort(key=lambda x: (x["word1"], x["word2"]))
    expected_pairs.sort(key=lambda x: (x["word1"], x["word2"]))

    assert pairs == expected_pairs
    logger.info("Extraction test passed successfully!")


def test_print_matrix_pairs(matrix, vectorizer, capsys):
    print("\n" + "="*50)
    print("RUNNING: test_print_matrix_pairs")
    logger.info("Starting print functionality test...")

    # We call the method, which should print internally
    pairs = LemmaMatrixBuilder.print_matrix_pairs(matrix, vectorizer)

    logger.info("Verifying sort order by weight (highest to lowest).")
    # Check sorting logic
    assert pairs[0]["weight"] == 3
    assert pairs[0]["word1"] == "apple"
    assert pairs[0]["word2"] == "banana"
    assert pairs[-1]["weight"] == 1

    logger.info("Verifying standard output capture.")
    # Check that the correct strings were actually printed to the console
    captured = capsys.readouterr()

    assert "apple <-> banana : 3" in captured.out
    assert "--- Extracted Word Pairs" in captured.out

    # Because capsys captures standard output, we need to print the captured
    # output ourselves if we actually want to see what the function printed during the test.
    print("[CAPTURED OUTPUT FROM FUNCTION]")
    print(captured.out)

    logger.info("Print functionality test passed successfully!")


def test_extract_matrix_pairs_empty_or_error(vectorizer):
    print("\n" + "="*50)
    print("RUNNING: test_extract_matrix_pairs_empty_or_error")
    logger.warning("Testing exception handling with None matrix (Expect an internal logger error below).")

    pairs = LemmaMatrixBuilder.extract_matrix_pairs(None, vectorizer)

    print(f"[TEST RUN] Returned pairs: {pairs}")
    assert pairs == []
    logger.info("Exception handling test passed successfully!")
