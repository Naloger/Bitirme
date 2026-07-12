"""Simple SQLModel ORM schema for Pages dataclasses.

This file provides lightweight ORM mappings for the Page, StructuredPage,
UnstructuredPage and WikiPage concepts defined in `Libs.Pages`.

Dependencies: sqlmodel

Usage:
    from sqlmodel import SQLModel, create_engine
    from backend.database.orm_schema import PageModel
    engine = create_engine("sqlite:///./test.db")
    SQLModel.metadata.create_all(engine)

The schema keeps lists/dicts in JSON columns for simplicity.
"""

from sqlalchemy import Column, MetaData, Text
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlmodel import Field, SQLModel
from typing import Dict, List

PAGES_METADATA = MetaData()


class PageSQLModel(SQLModel):
    __abstract__ = True
    metadata = PAGES_METADATA


class PageBase(PageSQLModel):
    id: str = Field(primary_key=True, index=True, max_length=36)
    creation_timestamp: float = Field(nullable=False)

# it should be made from a structured page
class StructuredPageModel(PageBase, table=True):
    __tablename__ = "structured_pages"

    unstructured_page_id: str = Field(default="", sa_column=Column(Text))
    # store list of triplets [[s,p,o], ...]
    triplets: list = Field(default_factory=list, sa_column=Column(SQLITE_JSON))
    structured_at: float = Field(nullable=False)
    transformed_to_graph: bool = False

class UnstructuredPageModel(PageBase, table=True):
    __tablename__ = "unstructured_pages"

    raw_text: str = Field(default="", sa_column=Column(Text))
    predicted_output: str = Field(default="", sa_column=Column(Text))
    prediction_error: float = Field(default=0.0)
    transformed_to_matrix: bool = Field(default=False, nullable=False)
    lemmatized_words: List[str] = Field(default_factory=list, sa_column=Column(SQLITE_JSON))

class WikiPageModel(PageSQLModel, table=True):
    __tablename__ = "wikified_pages"

    id: str = Field(primary_key=True, index=True, max_length=36)
    version: int = Field(nullable=False)

    title: str = Field(default="", max_length=512)
    body: str = Field(default="", sa_column=Column(Text))

    sections: List[Dict[str, str]] = Field(
        default_factory=list, sa_column=Column(SQLITE_JSON)
    )
    categories: List[str] = Field(default_factory=list, sa_column=Column(SQLITE_JSON))
    infobox: Dict[str, str] = Field(default_factory=dict, sa_column=Column(SQLITE_JSON))

    wikilinks: List[str] = Field(default_factory=list, sa_column=Column(SQLITE_JSON))
    interwiki_links: Dict[str, str] = Field(
        default_factory=dict, sa_column=Column(SQLITE_JSON)
    )
    external_links: List[Dict[str, str]] = Field(
        default_factory=list, sa_column=Column(SQLITE_JSON)
    )
    see_also: List[str] = Field(default_factory=list, sa_column=Column(SQLITE_JSON))

    references: List[Dict[str, str]] = Field(
        default_factory=list, sa_column=Column(SQLITE_JSON)
    )
    templates: List[str] = Field(default_factory=list, sa_column=Column(SQLITE_JSON))
    disambiguation: List[str] = Field(
        default_factory=list, sa_column=Column(SQLITE_JSON)
    )

    wikified_at: float = Field(nullable=False)
