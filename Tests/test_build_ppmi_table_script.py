from sqlmodel import Session, create_engine, select
import tempfile
from pathlib import Path

from backend.database.ORMSchemas.orm_schema_lemma_matrix import (
	LEMMA_MATRIX_METADATA,
	LemmaMatrixModel,
	PPMILemmaMatrixModel,
	VocabularyModel,
)
from Scripts.lemma.build_ppmi_table import rebuild_ppmi_table


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


def test_build_ppmi_table_function():
	# 1. Create a temporary file database
	with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
		tmp_path = Path(tmp.name)

	engine = None
	try:
		# 2. Initialize schema tables
		engine = create_engine(f"sqlite:///{tmp_path.as_posix()}")
		LEMMA_MATRIX_METADATA.create_all(engine)

		# 3. Populate mock co-occurrence data
		with Session(engine) as session:
			v1_id = _get_or_create_vocab_id(session, "apple")
			v2_id = _get_or_create_vocab_id(session, "banana")
			
			record = LemmaMatrixModel(id=1, vocab1_id=v1_id, vocab2_id=v2_id, weight=2)
			session.add(record)
			session.commit()

		# 4. Call the function directly with threshold = 0.0
		rebuild_ppmi_table(threshold=0.0, db_path=str(tmp_path))

		# Verify PPMI value in DB
		with Session(engine) as session:
			ppmi_records = session.exec(select(PPMILemmaMatrixModel)).all()
			assert len(ppmi_records) == 1
			assert ppmi_records[0].vocab1_id == v1_id
			assert ppmi_records[0].vocab2_id == v2_id
			assert abs(ppmi_records[0].weight - 1.0) < 1e-5

		# Call the function directly with threshold = 1.5 (should filter out)
		rebuild_ppmi_table(threshold=1.5, db_path=str(tmp_path))

		# Verify PPMI table is now empty
		with Session(engine) as session:
			ppmi_records = session.exec(select(PPMILemmaMatrixModel)).all()
			assert len(ppmi_records) == 0

	finally:
		if engine is not None:
			engine.dispose()
		# Clean up temporary database file
		if tmp_path.exists():
			tmp_path.unlink()


def test_build_ppmi_table_real_db():
	# 1. Obtain session to the real database (configured via LEMMA_MATRIX_DATABASE_PATH)
	from backend.api.api_init import get_lemma_matrix_session
	
	session_gen = get_lemma_matrix_session()
	session = next(session_gen)
	
	try:
		# 2. Populate mock co-occurrence data directly in the real database
		v1_id = _get_or_create_vocab_id(session, "hello")
		v2_id = _get_or_create_vocab_id(session, "world")
		
		record = LemmaMatrixModel(id=999, vocab1_id=v1_id, vocab2_id=v2_id, weight=5)
		session.add(record)
		session.commit()
		
		# 3. Run script rebuild logic (which reads from the real DB path and pushes to the real DB)
		rebuild_ppmi_table(threshold=0.0)
		
		# 4. Verify that PPMI scores were written to the real ppmi_lemma_matrix table
		ppmi_records = session.exec(select(PPMILemmaMatrixModel)).all()
		assert len(ppmi_records) >= 1
		# The record should match
		match = [r for r in ppmi_records if r.vocab1_id == v1_id and r.vocab2_id == v2_id]
		assert len(match) == 1
		assert abs(match[0].weight - 1.0) < 1e-5
		
	finally:
		# Close the session properly
		try:
			next(session_gen)
		except StopIteration:
			pass
