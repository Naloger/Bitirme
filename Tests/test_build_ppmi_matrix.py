import logging
import numpy as np
import scipy.sparse as sp

from Libs.PPMI.build_ppmi_matrix import build_ppmi_matrix_from_cooccurrence

# ==========================================
# Enhanced Logging Configuration
# ==========================================
class LogFormatter(logging.Formatter):
    """Custom formatter to make test results pop with ANSI colors."""
    GREY = "\x1b[38;20m"
    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    RESET = "\x1b[0m"
    FORMAT_STR = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def format(self, record):
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
    ch.setFormatter(LogFormatter())
    logger.addHandler(ch)

logger.propagate = False


def test_ppmi_basic_2x2():
    logger.info("Starting [test_ppmi_basic_2x2]")
    
    # Simple symmetric 2x2 cooccurrence matrix
    mat = np.array([[0, 2], [2, 0]])
    co = sp.csr_matrix(mat)
    logger.info("Input 2x2 cooccurrence matrix:\n%s", mat)

    vec, ppmi = build_ppmi_matrix_from_cooccurrence(None, co, threshold=0.0)
    arr = sp.csr_matrix(ppmi).toarray()
    logger.info("Calculated PPMI matrix:\n%s", arr)

    # Off-diagonals should be 1.0 (see calculation in implementation)
    assert arr.shape == (2, 2)
    assert np.allclose(arr[0, 1], 1.0)
    assert np.allclose(arr[1, 0], 1.0)
    assert arr[0, 0] == 0.0 and arr[1, 1] == 0.0
    logger.info("[CHECK] 2x2 shape and off-diagonal PPMI values of 1.0 verified.")
    logger.info("[PASS] test_ppmi_basic_2x2")


def test_ppmi_threshold_filters_out_values():
    logger.info("Starting [test_ppmi_threshold_filters_out_values]")
    
    mat = np.array([[0, 2], [2, 0]])
    co = sp.csr_matrix(mat)
    logger.info("Input cooccurrence matrix:\n%s", mat)

    # Threshold greater than computed PPMI (1.0) should drop values
    threshold = 1.1
    logger.info("Running PPMI build with threshold=%s", threshold)
    vec, ppmi = build_ppmi_matrix_from_cooccurrence(None, co, threshold=threshold)
    arr = sp.csr_matrix(ppmi).toarray()
    logger.info("Calculated PPMI matrix:\n%s", arr)

    assert np.allclose(arr, np.zeros_like(arr))
    logger.info("[CHECK] All values filtered out under threshold %s.", threshold)
    logger.info("[PASS] test_ppmi_threshold_filters_out_values")


def test_ppmi_symmetry_and_nonzero_positions():
    logger.info("Starting [test_ppmi_symmetry_and_nonzero_positions]")
    
    mat = np.array([[0, 2, 1], [2, 0, 3], [1, 3, 0]])
    co = sp.csr_matrix(mat)
    logger.info("Input 3x3 cooccurrence matrix:\n%s", mat)

    vec, ppmi = build_ppmi_matrix_from_cooccurrence(None, co, threshold=0.0)
    arr = sp.csr_matrix(ppmi).toarray()
    logger.info("Calculated PPMI matrix:\n%s", arr)

    # Result must be symmetric
    assert np.allclose(arr, arr.T)
    logger.info("[CHECK] Matrix symmetry verified.")

    # At least one off-diagonal should be non-zero
    off_diag = arr.copy()
    np.fill_diagonal(off_diag, 0)
    assert np.any(off_diag > 0)
    logger.info("[CHECK] Presence of non-zero off-diagonals verified.")
    logger.info("[PASS] test_ppmi_symmetry_and_nonzero_positions")


def test_vectorizer_passthrough_and_empty_matrix():
    logger.info("Starting [test_vectorizer_passthrough_and_empty_matrix]")
    
    mat = np.zeros((3, 3), dtype=int)
    co = sp.csr_matrix(mat)
    logger.info("Input empty 3x3 cooccurrence matrix.")

    dummy_vec = object()
    vec, ppmi = build_ppmi_matrix_from_cooccurrence(dummy_vec, co, threshold=0.0)
    arr = sp.csr_matrix(ppmi).toarray()
    logger.info("Calculated PPMI matrix:\n%s", arr)

    # Vectorizer is returned unchanged
    assert vec is dummy_vec
    logger.info("[CHECK] Vectorizer object passed through successfully.")

    # Empty input should return an all-zero matrix
    assert isinstance(ppmi, sp.spmatrix)
    assert np.allclose(arr, np.zeros((3, 3)))
    logger.info("[CHECK] All-zero matrix returned successfully.")
    logger.info("[PASS] test_vectorizer_passthrough_and_empty_matrix")


def test_ppmi_vectorized_edge_cases_and_correctness():
    logger.info("Starting [test_ppmi_vectorized_edge_cases_and_correctness]")
    
    # Test matrix with zeroes, diagonals, and valid off-diagonal values
    # Shape 4x4
    mat = np.array([
        [0,  5,  0,  0],  # Diagonal is 0, (0,1) is 5, (0,2) is 0, (0,3) is zero
        [5,  0,  2,  0],  # (1,2) is 2
        [0,  2,  0,  1],  # (2,3) is 1
        [0,  0,  1,  0]   
    ])
    co = sp.csr_matrix(mat)
    logger.info("Input 4x4 cooccurrence matrix:\n%s", mat)
    
    vec, ppmi = build_ppmi_matrix_from_cooccurrence(None, co, threshold=0.0)
    arr = sp.csr_matrix(ppmi).toarray()
    logger.info("Calculated PPMI matrix:\n%s", arr)
    
    # Assert diagonal remains 0
    assert np.all(np.diagonal(arr) == 0.0)
    logger.info("[CHECK] Diagonal remains zero.")
    
    # Zero entries should be filtered out / remain zero
    assert arr[0, 3] == 0.0
    assert arr[3, 0] == 0.0
    assert arr[0, 2] == 0.0
    assert arr[2, 0] == 0.0
    logger.info("[CHECK] Zero-value co-occurrences remain zero in PPMI.")
    
    # Valid non-zero off-diagonals must be symmetric and positive
    assert arr[0, 1] > 0.0
    assert arr[1, 0] == arr[0, 1]
    assert arr[1, 2] > 0.0
    assert arr[2, 1] == arr[1, 2]
    assert arr[2, 3] > 0.0
    assert arr[3, 2] == arr[2, 3]
    logger.info("[CHECK] All positive co-occurrences produced positive symmetric PPMI values.")
    logger.info("[PASS] test_ppmi_vectorized_edge_cases_and_correctness")


