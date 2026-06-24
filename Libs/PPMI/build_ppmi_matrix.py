"""Build a Positive Pointwise Mutual Information (PPMI) matrix

This module provides a helper to convert a co-occurrence matrix (as produced
by `services.Libs.Lemmatizer.lemma_matrix.LemmaMatrixBuilder.build_cooccurrence_matrix`)
into a PPMI-weighted matrix. The output shape and the associated vectorizer
are compatible with the rest of the project's utilities (e.g. printing and
pair extraction).

Usage:
	vectorizer, cooccurrence = LemmaMatrixBuilder().build_cooccurrence_matrix(texts)
	vectorizer, ppmi = build_ppmi_matrix_from_cooccurrence(vectorizer, cooccurrence, threshold=0.5)

The `threshold` filters PPMI values: values below the threshold are dropped
from the sparse matrix (set to zero) which helps downstream storage and
filtering.
"""

from __future__ import annotations

import logging
from typing import Tuple

import numpy as np
import scipy.sparse as sp

logger = logging.getLogger(__name__)


def build_ppmi_matrix_from_cooccurrence(
	vectorizer,
	cooccurrence: sp.spmatrix,
	threshold: float = 0.0,
) -> Tuple[object, sp.spmatrix]:
	"""Convert a co-occurrence sparse matrix to a PPMI sparse matrix.

	Args:
		vectorizer: the CountVectorizer (or any object with get_feature_names_out)
			returned by the lemma matrix builder. This function returns the
			same vectorizer for compatibility with other helpers.
		cooccurrence: square scipy sparse matrix (term x term) with integer
			co-occurrence counts. Diagonal values are expected to be zero or
			will be ignored.
		threshold: float >= 0. Values of PPMI below this threshold will be
			removed from the resulting sparse matrix (sparsification).

	Returns:
		(vectorizer, ppmi_matrix) where ppmi_matrix is a scipy CSR sparse
		matrix with PPMI scores and the same shape as `cooccurrence`.
	"""

	if not sp.isspmatrix(cooccurrence):
		logger.error("Invalid type for cooccurrence: %s", type(cooccurrence))
		raise TypeError("cooccurrence must be a scipy sparse matrix")

	# Convert to a concrete COO matrix for attribute access and iteration
	coo = sp.coo_matrix(cooccurrence)

	# Log input summary
	try:
		logger.debug(
			"PPMI input: shape=%s, nnz=%d, dtype=%s, threshold=%s",
			coo.shape,
			coo.nnz,
			getattr(coo, "dtype", None),
			threshold,
		)
	except Exception:
		logger.debug("PPMI input: unable to log detailed cooccurrence info")

	# For tracing, either log the full matrix (when small) or top-k pairs
	try:
		max_full = 10
		if coo.shape[0] <= max_full and coo.shape[1] <= max_full:
			logger.info("PPMI input full matrix:\n%s", sp.csr_matrix(coo).toarray())
		else:
			# log top-k cooccurrence counts
			top_k = 10
			rows = np.asarray(coo.row)
			cols = np.asarray(coo.col)
			data_vals = np.asarray(coo.data)
			if data_vals.size:
				order = np.argsort(data_vals)[::-1][:top_k]
				top = [f"({int(rows[i])},{int(cols[i])})={float(data_vals[i])}" for i in order]
				logger.info("PPMI input top %d cooccurrence entries: %s", top_k, top)
			else:
				logger.info("PPMI input has no non-zero cooccurrence entries")
	except Exception:
		logger.debug("PPMI input: failed to produce detailed trace")

	# Row sums give marginal counts for each term. Use the concrete object
	# so static analyzers can resolve the `sum` attribute.
	row_sum = np.asarray(coo.sum(axis=1)).ravel()
	total = float(row_sum.sum())

	if total <= 0 or row_sum.size == 0:
		# Empty matrix — return an empty float CSR matrix of the same shape
		logger.warning("Cooccurrence matrix is empty or has no counts. Returning empty PPMI matrix.")
		empty = sp.csr_matrix(cooccurrence.shape, dtype=float)
		return vectorizer, empty

	# Vectorized filtering of diagonal and non-positive entries
	valid_mask = (coo.row != coo.col) & (coo.data > 0)
	filtered_rows = coo.row[valid_mask]
	filtered_cols = coo.col[valid_mask]
	filtered_data = coo.data[valid_mask]

	if filtered_data.size == 0:
		logger.info("No PPMI values passed the threshold=%s; returning empty matrix.", threshold)
		empty = sp.csr_matrix(cooccurrence.shape, dtype=float)
		return vectorizer, empty

	# Vectorized PPMI calculation
	# pmi = log2( (v / total) / ((row_sum[i] / total) * (row_sum[j] / total)) )
	# pmi = log2( (v * total) / (row_sum[i] * row_sum[j]) )
	p_i = row_sum[filtered_rows]
	p_j = row_sum[filtered_cols]

	# Compute PMI and clip negative values to 0 to get PPMI.
	# We use np.errstate to suppress warnings for division-by-zero or log2(<=0)
	# and clean any NaNs or infinite values to 0.0.
	with np.errstate(divide='ignore', invalid='ignore'):
		ratio = (filtered_data * total) / (p_i * p_j)
		pmi = np.log2(ratio)
	
	pmi = np.nan_to_num(pmi, nan=0.0, posinf=0.0, neginf=0.0)
	ppmi = np.maximum(pmi, 0.0)

	# Filter based on threshold
	threshold_mask = ppmi >= threshold
	final_rows = filtered_rows[threshold_mask]
	final_cols = filtered_cols[threshold_mask]
	final_ppmi = ppmi[threshold_mask]

	if final_ppmi.size == 0:
		logger.info("No PPMI values passed the threshold=%s; returning empty matrix.", threshold)
		empty = sp.csr_matrix(cooccurrence.shape, dtype=float)
		return vectorizer, empty

	ppmi_coo = sp.coo_matrix((final_ppmi, (final_rows, final_cols)), shape=cooccurrence.shape)

	# Ensure symmetry: if only one triangle was populated, mirror it.
	# We add the transpose and divide by 2 to keep values consistent when duplicates exist.
	ppmi_sym = (ppmi_coo + ppmi_coo.T) / 2.0

	result = ppmi_sym.tocsr()
	try:
		logger.debug(
			"PPMI output: shape=%s, nnz=%d, density=%.6f",
			result.shape,
			result.nnz,
			float(result.nnz) / (result.shape[0] * max(1, result.shape[1])),
		)
	except Exception:
		logger.debug("PPMI output: unable to compute detailed stats")

	# For tracing, log the full PPMI matrix for small sizes, otherwise top-k PPMI values
	try:
		max_full = 10
		if result.shape[0] <= max_full and result.shape[1] <= max_full:
			logger.info("PPMI output full matrix:\n%s", result.toarray())
		else:
			top_k = 10
			res_coo = sp.coo_matrix(result)
			res_rows = np.asarray(res_coo.row)
			res_cols = np.asarray(res_coo.col)
			res_data = np.asarray(res_coo.data)
			if res_data.size:
				order = np.argsort(res_data)[::-1][:top_k]
				top = [f"({int(res_rows[i])},{int(res_cols[i])})={float(res_data[i]):.4f}" for i in order]
				logger.info("PPMI output top %d entries: %s", top_k, top)
			else:
				logger.info("PPMI output has no non-zero entries")
	except Exception:
		logger.debug("PPMI output: failed to produce detailed trace")

	return vectorizer, result

