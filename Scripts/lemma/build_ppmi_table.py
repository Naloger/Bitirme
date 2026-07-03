"""Rebuild the ppmi_lemma_matrix table from lemma_matrix table in lemma_matrix.db."""

from __future__ import annotations

import math
from collections import defaultdict

# Add backend directory to Python path if running script directly
# sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlmodel import  select, delete
from Config.config import LEMMA_MATRIX_DATABASE_PATH, BUILD_PPMI_THRESHOLD
from backend.database.init_db import init_db
from backend.database.ORMSchemas.orm_schema_lemma_matrix import (
	LEMMA_MATRIX_METADATA,
	LemmaMatrixModel,
	PPMILemmaMatrixModel,
	ConceptsModel,
	ConceptConnectionsModel,
)


def rebuild_ppmi_table(threshold: float | None = None, db_path: str | None = None) -> None:
	"""Read lemma_matrix table, calculate PPMI scores, and populate ppmi_lemma_matrix table."""
	target_threshold = threshold if threshold is not None else BUILD_PPMI_THRESHOLD
	target_db_path = db_path or LEMMA_MATRIX_DATABASE_PATH

	print(f"Initializing database connection to: {target_db_path}")
	engine, session_factory = init_db(db_path=target_db_path, metadata=LEMMA_MATRIX_METADATA, echo=False)

	try:
		with session_factory() as session:
			print("Reading co-occurrence counts from lemma_matrix table...")
			# Select all records from the lemma_matrix
			records = session.exec(select(LemmaMatrixModel)).all()
			if not records:
				print("The lemma_matrix table is empty. No co-occurrences to process.")
				return

			print(f"Loaded {len(records)} co-occurrence pairs. Calculating marginal counts...")

			# Compute marginal counts C(u) for each word, and total sum N of raw weights
			marginal_counts: dict[int, float] = defaultdict(float)
			total_edge_weight = 0.0

			for r in records:
				w = float(r.weight)
				marginal_counts[r.vocab1_id] += w
				marginal_counts[r.vocab2_id] += w
				total_edge_weight += w

			# Total sum of symmetric co-occurrence matrix is T = 2 * N
			T = 2.0 * total_edge_weight
			print(f"Total undirected co-occurrence sum (N): {total_edge_weight:.2f}")
			print(f"Symmetric total sum (T): {T:.2f}")

			print(f"Calculating PPMI scores (threshold >= {target_threshold})...")
			ppmi_records: list[PPMILemmaMatrixModel] = []
			next_ppmi_id = 1

			for r in records:
				w = float(r.weight)
				c_i = marginal_counts[r.vocab1_id]
				c_j = marginal_counts[r.vocab2_id]

				if c_i > 0 and c_j > 0 and w > 0:
					# PPMI(i, j) = max(0, log2( (w * T) / (c_i * c_j) ))
					ratio = (w * T) / (c_i * c_j)
					pmi = math.log2(ratio)
					ppmi = max(0.0, pmi)
				else:
					ppmi = 0.0

				if ppmi >= target_threshold:
					ppmi_records.append(
						PPMILemmaMatrixModel(
							id=next_ppmi_id,
							vocab1_id=r.vocab1_id,
							vocab2_id=r.vocab2_id,
							weight=ppmi,
						)
					)
					next_ppmi_id += 1

			print(f"Calculated PPMI values: {len(ppmi_records)} out of {len(records)} pairs passed the threshold.")

			print("Clearing existing PPMI, concepts, and concept_connections tables...")
			session.exec(delete(ConceptConnectionsModel))
			session.exec(delete(ConceptsModel))
			session.exec(delete(PPMILemmaMatrixModel))
			session.commit()

			if ppmi_records:
				print(f"Pushing {len(ppmi_records)} PPMI records to the database in batches...")
				batch_size = 1000
				for i in range(0, len(ppmi_records), batch_size):
					batch = ppmi_records[i : i + batch_size]
					session.add_all(batch)
					session.commit()
				print("PPMI table populated successfully!")
			else:
				print("No PPMI records to write.")
	finally:
		engine.dispose()


if __name__ == "__main__":
	# Default execution parameters from config
	rebuild_ppmi_table()
