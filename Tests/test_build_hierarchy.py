from sqlmodel import Session, create_engine, select
import tempfile
from pathlib import Path

from backend.database.ORMSchemas.orm_schema_lemma_matrix import (
	LEMMA_MATRIX_METADATA,
	VocabularyModel,
	PPMILemmaMatrixModel,
	ConceptsModel,
	ConceptConnectionsModel,
)
from Scripts.lemma.build_hierarchy import build_taxonomy_hierarchy


def _get_or_create_vocab_id(session: Session, word: str) -> int:
	"""Helper to get or create vocabulary entry and return its ID."""
	existing = session.exec(select(VocabularyModel).where(VocabularyModel.word == word)).first()
	if existing:
		assert existing.id is not None
		return existing.id
	new_vocab = VocabularyModel(word=word)
	session.add(new_vocab)
	session.flush()
	assert new_vocab.id is not None
	return new_vocab.id


def test_build_taxonomy_hierarchy():
	# 1. Create a temporary SQLite database file
	with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
		tmp_path = Path(tmp.name)

	engine = None
	try:
		# 2. Initialize schema tables
		engine = create_engine(f"sqlite:///{tmp_path.as_posix()}")
		LEMMA_MATRIX_METADATA.create_all(engine)

		# 3. Insert mock PPMI data representing two distinct clusters connected by a weak bridge
		# Cluster 1 (Fruit): apple, banana, orange
		# Cluster 2 (Vehicles): car, truck, bus
		# Bridge: apple <-> car
		mock_edges = [
			# Fruit cluster
			("apple", "banana", 5.0),
			("apple", "orange", 5.0),
			# Vehicle cluster
			("car", "truck", 6.0),
			("car", "bus", 6.0),
			# Weak bridge
			("apple", "car", 0.5),
		]

		with Session(engine) as session:
			for idx, (w1, w2, weight) in enumerate(mock_edges):
				v1_id = _get_or_create_vocab_id(session, w1)
				v2_id = _get_or_create_vocab_id(session, w2)
				record = PPMILemmaMatrixModel(id=idx + 1, vocab1_id=v1_id, vocab2_id=v2_id, weight=weight)
				session.add(record)
			session.commit()

		# 4. Call hierarchical collapse function
		build_taxonomy_hierarchy(max_levels=4, db_path=str(tmp_path))

		# 5. Connect and assert taxonomic properties
		with Session(engine) as session:
			# Verify Level 0 Concepts
			level_0 = session.exec(select(ConceptsModel).where(ConceptsModel.level == 0)).all()
			# Should have exactly 6 base concepts (apple, banana, orange, car, truck, bus)
			assert len(level_0) == 6
			
			# Verify Level 1 Concepts (should be clustered into 2 communities: fruits and vehicles)
			level_1 = session.exec(select(ConceptsModel).where(ConceptsModel.level == 1)).all()
			assert len(level_1) == 2
			
			# Confirm labels match centroids (apple should be fruit leader, car should be vehicle leader)
			labels = {c.label for c in level_1}
			assert "apple" in labels
			assert "car" in labels

			# Verify Level 1 Connections
			level_1_conns = session.exec(select(ConceptConnectionsModel).where(ConceptConnectionsModel.level == 1)).all()
			# There should be exactly 1 connection representing the bridge between fruit parent and vehicle parent
			assert len(level_1_conns) == 1
			# Weight should match the bridge weight of 0.5
			assert abs(level_1_conns[0].weight - 0.5) < 1e-5

			# Verify Level 2 Concepts (bridge collapses the 2 Level 1 concepts into 1 root concept)
			level_2 = session.exec(select(ConceptsModel).where(ConceptsModel.level == 2)).all()
			assert len(level_2) == 1
			
			# Parent assignment check
			# Level 1 concepts should point to Level 2 root concept as parent
			root_id = level_2[0].id
			assert root_id is not None
			for c1 in level_1:
				assert c1.parent_id == root_id

	finally:
		if engine is not None:
			engine.dispose()
		# Clean up temporary database file
		if tmp_path.exists():
			tmp_path.unlink()
