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


def _next_matrix_id(session: Session) -> int:
	max_id = session.exec(select(func.max(LemmaMatrixModel.id))).one()
	return int(max_id or 0) + 1


@app.post(
	"/api/lemma/connections",
	response_model=dict,
	tags=["LemmaConnections"],
)
def save_connections(payload: List[LemmaConnectionCreate], session: Session = Depends(get_lemma_matrix_session)):
	"""Receives a list of (owner_id, word1, word2, weight) rows and bulk-inserts them into the lemma matrix DB."""
	next_id = _next_matrix_id(session)
	db_records = [
		LemmaMatrixModel(
			id=next_id + index,
			owner_id=item.owner_id or 0,
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
	"/api/lemma/connections",
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
	"/api/lemma/connections/{conn_id}",
	response_model=LemmaConnectionRead,
	tags=["LemmaConnections"],
)
def get_connection(conn_id: int, session: Session = Depends(get_lemma_matrix_session)):
	conn = session.exec(select(LemmaMatrixModel).where(LemmaMatrixModel.id == conn_id)).first()
	if not conn:
		raise HTTPException(status_code=404, detail="Connection not found")
	return conn


@app.put(
	"/api/lemma/connections/{conn_id}",
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
