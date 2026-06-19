import numpy as np
import scipy.sparse as sp

from Libs.PPMI.build_ppmi_matrix import build_ppmi_matrix_from_cooccurrence


def test_ppmi_basic_2x2():
    # Simple symmetric 2x2 cooccurrence matrix
    mat = np.array([[0, 2], [2, 0]])
    co = sp.csr_matrix(mat)

    vec, ppmi = build_ppmi_matrix_from_cooccurrence(None, co, threshold=0.0)
    arr = sp.csr_matrix(ppmi).toarray()

    # Off-diagonals should be 1.0 (see calculation in implementation)
    assert arr.shape == (2, 2)
    assert np.allclose(arr[0, 1], 1.0)
    assert np.allclose(arr[1, 0], 1.0)
    assert arr[0, 0] == 0.0 and arr[1, 1] == 0.0


def test_ppmi_threshold_filters_out_values():
    mat = np.array([[0, 2], [2, 0]])
    co = sp.csr_matrix(mat)

    # Threshold greater than computed PPMI (1.0) should drop values
    vec, ppmi = build_ppmi_matrix_from_cooccurrence(None, co, threshold=1.1)
    arr = sp.csr_matrix(ppmi).toarray()

    assert np.allclose(arr, np.zeros_like(arr))


def test_ppmi_symmetry_and_nonzero_positions():
    mat = np.array([[0, 2, 1], [2, 0, 3], [1, 3, 0]])
    co = sp.csr_matrix(mat)

    vec, ppmi = build_ppmi_matrix_from_cooccurrence(None, co, threshold=0.0)
    arr = sp.csr_matrix(ppmi).toarray()

    # Result must be symmetric
    assert np.allclose(arr, arr.T)

    # At least one off-diagonal should be non-zero
    off_diag = arr.copy()
    np.fill_diagonal(off_diag, 0)
    assert np.any(off_diag > 0)


def test_vectorizer_passthrough_and_empty_matrix():
    mat = np.zeros((3, 3), dtype=int)
    co = sp.csr_matrix(mat)

    dummy_vec = object()
    vec, ppmi = build_ppmi_matrix_from_cooccurrence(dummy_vec, co, threshold=0.0)

    # Vectorizer is returned unchanged
    assert vec is dummy_vec

    # Empty input should return an all-zero matrix
    assert isinstance(ppmi, sp.spmatrix)
    assert np.allclose(sp.csr_matrix(ppmi).toarray(), np.zeros((3, 3)))

