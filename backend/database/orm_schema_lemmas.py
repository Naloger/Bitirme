"""Simple SQLModel ORM schema for Document and Keyword Search/Lemma Matrix.

The schema keeps lists/dicts in JSON columns for simplicity.
"""

from sqlalchemy import Column, MetaData, Text, Index
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlmodel import Field, SQLModel
from typing import List
import time

LEMMAS_METADATA = MetaData()

class LemmaSQLModel(SQLModel):
    __abstract__ = True
    metadata = LEMMAS_METADATA


# Document tablosu: raw text, timestamp ve document'in bağlı olduğu lemmalar
class DocumentModel(LemmaSQLModel, table=True):
    __tablename__ = "documents"

    id: str = Field(primary_key=True, index=True, max_length=36)
    timestamp: float = Field(default_factory=time.time, nullable=False)
    raw_text: str = Field(default="", sa_column=Column(Text))

    # Document'in bağlı olduğu lemma/keyword listesi (JSON array)
    lemmas: List[str] = Field(default_factory=list, sa_column=Column(SQLITE_JSON))


# Ayrı olarak tutulan Lemma (Keyword) Matrisi
# Graph-style connections between tokens (word1, word2, weight)
class LemmaMatrixModel(LemmaSQLModel, table=True):
    __tablename__ = "lemma_matrix"

    # Graph kenarları (edges) için integer primary key
    id: int = Field(default=None, primary_key=True)

    word1: str = Field(sa_column=Column(Text, nullable=False))
    word2: str = Field(sa_column=Column(Text, nullable=False))
    weight: int = Field(default=0, nullable=False)

# Sorgu performansını artırmak için Index tanımlamaları (İsteğe bağlı)
Index("ix_lemma_matrix_words", LemmaMatrixModel.word1, LemmaMatrixModel.word2)
