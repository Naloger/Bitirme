"""Lemma matrix endpoints: store graph-edge triples (word1:str, word2:str, weight:int)."""
from typing import List

from fastapi import Depends, Query, HTTPException
from sqlmodel import Session, select

from backend.api.api_data_schemas_lemma import (
    LemmaConnectionCreate,
    LemmaConnectionRead,
    LemmaConnectionUpdate,
)
from backend.api.api_init import app, get_lemma_session
from backend.database.orm_schema_lemmas import LemmaMatrixModel


# DÜZELTME 1: Yeni modelimizi (LemmaMatrixModel) import etmeliyiz.
# Not: Import yolunu (backend.models) kendi proje yapına göre düzenlemelisin.


@app.post(
    "/api/lemma/connections",
    response_model=dict,
    tags=["LemmaConnections"],
)
def save_connections(payload: List[LemmaConnectionCreate], session: Session = Depends(get_lemma_session)):
    """Receives a list of (word1, word2, weight) triples and bulk-inserts them into the lemma matrix DB.

    Types are strictly: word1:str, word2:str, weight:int
    """
    # DÜZELTME 2: LemmaConnectionModel yerine yeni ismimiz olan LemmaMatrixModel'i kullanıyoruz.
    db_records = [
        LemmaMatrixModel(word1=item.word1, word2=item.word2, weight=item.weight)
        for item in payload
    ]

    # Bulk save
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
        session: Session = Depends(get_lemma_session),
):
    # DÜZELTME 3: select sorgusunda LemmaMatrixModel kullanıyoruz.
    statement = select(LemmaMatrixModel).offset(skip).limit(limit)
    return session.exec(statement).all()


@app.get(
    "/api/lemma/connections/{conn_id}",
    response_model=LemmaConnectionRead,
    tags=["LemmaConnections"],
)
def get_connection(conn_id: int, session: Session = Depends(get_lemma_session)):
    # DÜZELTME 4: Veritabanından veriyi çekerken LemmaMatrixModel kullanıyoruz.
    conn = session.get(LemmaMatrixModel, conn_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return conn


@app.put(
    "/api/lemma/connections/{conn_id}",
    response_model=LemmaConnectionRead,
    tags=["LemmaConnections"],
)
def update_connection(conn_id: int, payload: LemmaConnectionUpdate, session: Session = Depends(get_lemma_session)):
    # DÜZELTME 5: Güncelleme işleminde de LemmaMatrixModel kullanıyoruz.
    conn = session.get(LemmaMatrixModel, conn_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(conn, key, value)

    session.add(conn)
    session.commit()
    session.refresh(conn)

    return conn
