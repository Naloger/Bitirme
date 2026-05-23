"""Simple SQLModel ORM schema for Keywords dataclasses.

The schema keeps lists/dicts in JSON columns for simplicity.
"""
from sqlalchemy import Column, MetaData, Text
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlmodel import Field, SQLModel
from typing import List

KEYWORDS_METADATA = MetaData()


class KeywordSQLModel(SQLModel):
    __abstract__ = True
    metadata = KEYWORDS_METADATA


class KeywordModel(KeywordSQLModel, table=True):
    __tablename__ = "keywords"

    id: str = Field(primary_key=True, index=True, max_length=36)
    creation_timestamp: float = Field(nullable=False)
    raw_text: str = Field(default="", sa_column=Column(Text))
    keywords: List[str] = Field(default_factory=list, sa_column=Column(SQLITE_JSON))
