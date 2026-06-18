"""Simple SQLModel ORM schema for Document and Keyword Search/Lemma Matrix.

The schema keeps lists/dicts in JSON columns for simplicity.
"""

from sqlalchemy import Column, MetaData, Text
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
    transformed_to_matrix : bool = Field(default=False, sa_column=Column(SQLITE_JSON))
