from sqlalchemy import Column, MetaData, Text, Index
from sqlmodel import Field, SQLModel
LEMMA_MATRIX_METADATA = MetaData()

class LemmaMatrixSQLModel(SQLModel):
    __abstract__ = True
    metadata = LEMMA_MATRIX_METADATA
# Ayrı olarak tutulan Lemma (Keyword) Matrisi
# Graph-style connections between tokens (word1, word2, weight)
class LemmaMatrixModel(LemmaMatrixSQLModel, table=True):
    __tablename__ = "lemma_matrix"

    # Graph kenarları (edges) için integer primary key
    id: int = Field(default=None, primary_key=True)
    word1: str = Field(sa_column=Column(Text, primary_key=True, nullable=False))
    word2: str = Field(sa_column=Column(Text, primary_key=True, nullable=False))
    weight: int = Field(default=0, nullable=False)

class PPMILemmaMatrixModel(LemmaMatrixSQLModel, table=True):
    __tablename__ = "ppmi_lemma_matrix"

    # Graph kenarları (edges) için integer primary key
    id: int = Field(default=None, primary_key=True)
    word1: str = Field(sa_column=Column(Text, primary_key=True, nullable=False))
    word2: str = Field(sa_column=Column(Text, primary_key=True, nullable=False))
    weight: int = Field(default=0, nullable=False)

# Sorgu performansını artırmak için Index tanımlamaları (İsteğe bağlı)
Index("ix_lemma_matrix_words", LemmaMatrixModel.word1, LemmaMatrixModel.word2)
Index("ix_ppmi_lemma_matrix_words", PPMILemmaMatrixModel.word1, PPMILemmaMatrixModel.word2)
