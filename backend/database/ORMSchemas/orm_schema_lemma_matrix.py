from typing import Optional
from sqlalchemy import Column, MetaData, Text
from sqlmodel import Field, SQLModel

LEMMA_MATRIX_METADATA = MetaData()


class LemmaMatrixSQLModel(SQLModel):
    __abstract__ = True
    metadata = LEMMA_MATRIX_METADATA


# --- Table 0: vocabulary ---
class VocabularyModel(LemmaMatrixSQLModel, table=True):
    __tablename__ = "vocabulary"

    id: Optional[int] = Field(default=None, primary_key=True)
    word: str = Field(sa_column=Column(Text, unique=True, index=True, nullable=False))


# --- Table 1: lemma_matrix ---
class LemmaMatrixModel(LemmaMatrixSQLModel, table=True):
    __tablename__ = "lemma_matrix"

    id: Optional[int] = Field(default=None, primary_key=True)
    vocab1_id: int = Field(foreign_key="vocabulary.id", index=True, nullable=False)
    vocab2_id: int = Field(foreign_key="vocabulary.id", index=True, nullable=False)
    weight: int = Field(index=True, default=0, nullable=False)


# --- Table 2: ppmi_lemma_matrix ---
class PPMILemmaMatrixModel(LemmaMatrixSQLModel, table=True):
    __tablename__ = "ppmi_lemma_matrix"

    id: Optional[int] = Field(default=None, primary_key=True)
    vocab1_id: int = Field(foreign_key="vocabulary.id", index=True, nullable=False)
    vocab2_id: int = Field(foreign_key="vocabulary.id", index=True, nullable=False)
    weight: float = Field(index=True, default=0.0, nullable=False)


# --- Table 3: concepts ---
class ConceptsModel(LemmaMatrixSQLModel, table=True):
    __tablename__ = "concepts"

    id: Optional[int] = Field(default=None, primary_key=True)
    level: int = Field(index=True, nullable=False)
    parent_id: Optional[int] = Field(default=None, foreign_key="concepts.id", index=True, nullable=True)
    vocab_id: Optional[int] = Field(default=None, foreign_key="vocabulary.id", index=True, nullable=True)
    label: Optional[str] = Field(default=None, index=True, nullable=True)
    llm_label: Optional[str] = Field(default=None, index=True, nullable=True)
    summary: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    pagerank_score: Optional[float] = Field(default=None, nullable=True)
    is_leader: Optional[bool] = Field(default=None, index=True, nullable=True)


# --- Table 4: concept_connections ---
class ConceptConnectionsModel(LemmaMatrixSQLModel, table=True):
    __tablename__ = "concept_connections"

    id: Optional[int] = Field(default=None, primary_key=True)
    level: int = Field(index=True, nullable=False)
    node1_id: int = Field(foreign_key="concepts.id", index=True, nullable=False)
    node2_id: int = Field(foreign_key="concepts.id", index=True, nullable=False)
    weight: float = Field(default=0.0, nullable=False)
