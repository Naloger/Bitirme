"""Lemma matrix endpoints: store graph-edge triples with owner IDs."""

from typing import List

from fastapi import Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from backend.api.api_data_schemas_lemma_matrix import (
	LemmaConnectionCreate,
	LemmaConnectionRead,
	LemmaConnectionUpdate,
)
from backend.api.api_init import app, get_lemma_matrix_session
from backend.database.orm_schema_lemma_matrix import LemmaMatrixModel
from pydantic import BaseModel, model_validator
from typing import Optional

# Lemmatizer
from Libs.Lemmatizer.lemma_matrix import LemmaMatrixBuilder


def _next_matrix_id(session: Session) -> int:
	max_id = session.exec(select(func.max(LemmaMatrixModel.id))).one()
	return int(max_id or 0) + 1


@app.post(
	"/api/lemma_matrix/connections",
	response_model=dict,
	tags=["LemmaConnections"],
)
def save_connections(payload: List[LemmaConnectionCreate], session: Session = Depends(get_lemma_matrix_session)):
	"""Receives a list of ( word1, word2, weight) rows and bulk-inserts them into the lemma matrix DB."""
	next_id = _next_matrix_id(session)
	db_records = [
		LemmaMatrixModel(
			id=next_id + index,
			word1=item.word1,
			word2=item.word2,
			weight=item.weight,
		)
		for index, item in enumerate(payload)
	]

	session.add_all(db_records)
	session.commit()

	return {"message": f"Successfully saved {len(db_records)} connections to the matrix database!"}


@app.get(
	"/api/lemma_matrix/connections",
	response_model=list[LemmaConnectionRead],
	tags=["LemmaConnections"],
)
def get_all_connections(
	skip: int = Query(0, ge=0),
	limit: int = Query(100, ge=1, le=500),
	session: Session = Depends(get_lemma_matrix_session),
):
	statement = select(LemmaMatrixModel).offset(skip).limit(limit)
	return session.exec(statement).all()


@app.get(
	"/api/lemma_matrix/connections/{conn_id}",
	response_model=LemmaConnectionRead,
	tags=["LemmaConnections"],
)
def get_connection(conn_id: int, session: Session = Depends(get_lemma_matrix_session)):
	conn = session.exec(select(LemmaMatrixModel).where(LemmaMatrixModel.id == conn_id)).first()
	if not conn:
		raise HTTPException(status_code=404, detail="Connection not found")
	return conn


@app.put(
	"/api/lemma_matrix/connections/{conn_id}",
	response_model=LemmaConnectionRead,
	tags=["LemmaConnections"],
)
def update_connection(conn_id: int, payload: LemmaConnectionUpdate, session: Session = Depends(get_lemma_matrix_session)):
	conn = session.exec(select(LemmaMatrixModel).where(LemmaMatrixModel.id == conn_id)).first()
	if not conn:
		raise HTTPException(status_code=404, detail="Connection not found")

	update_data = payload.model_dump(exclude_unset=True)
	for key, value in update_data.items():
		setattr(conn, key, value)

	session.add(conn)
	session.commit()
	session.refresh(conn)

	return conn


# Payload model for building matrix from text(s)
class TextsPayload(BaseModel):
	text: Optional[str] = None
	texts: Optional[list[str]] = None
	min_weight: int = 1

	@model_validator(mode="after")
	def at_least_one(self):
		# Instance-level validator: ensure at least one of text/texts provided
		if not self.text and not self.texts:
			raise ValueError("Either 'text' or 'texts' must be provided")
		return self


@app.post(
	"/api/lemma_matrix/build",
	response_model=dict,
	tags=["LemmaConnections"],
)
def build_matrix_from_text(payload: TextsPayload, session: Session = Depends(get_lemma_matrix_session)):
	"""Accepts a single text or a list of texts, builds a lemmatized co-occurrence matrix,
	extracts word pairs and stores them into the lemma matrix database.
	"""
	# Prepare texts list
	texts: list[str] = []
	if payload.text:
		texts.append(payload.text)
	if payload.texts:
		texts.extend(payload.texts)

	if not texts:
		raise HTTPException(status_code=400, detail="No text provided")

	builder = LemmaMatrixBuilder()
	vectorizer, matrix = builder.build_cooccurrence_matrix(texts)
	pairs = builder.extract_matrix_pairs(matrix, vectorizer)

	# Optionally filter by min_weight
	if payload.min_weight and payload.min_weight > 1:
		pairs = [p for p in pairs if p["weight"] >= payload.min_weight]

	if not pairs:
		return {"message": "No co-occurrence pairs found for the provided text(s)."}

	# Persist to DB with incremental ids
	next_id = _next_matrix_id(session)
	db_records = []
	for index, item in enumerate(pairs):
		db_records.append(
			LemmaMatrixModel(
				id=next_id + index,
				word1=item["word1"],
				word2=item["word2"],
				weight=item["weight"],
			)
		)

	session.add_all(db_records)
	session.commit()

	return {"message": f"Successfully built and saved {len(db_records)} connections to the matrix database!"}

