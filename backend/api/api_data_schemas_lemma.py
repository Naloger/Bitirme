from typing import List
from sqlmodel import SQLModel


# Connection schema used to represent graph edges between lemma tokens.
# Datatypes are restricted to: str, str, int (word1, word2, weight)
class LemmaConnectionCreate(SQLModel):
    word1: str
    word2: str
    weight: int


class LemmaConnectionRead(LemmaConnectionCreate):
    id: int


class LemmaConnectionUpdate(SQLModel):
    word1: str | None = None
    word2: str | None = None
    weight: int | None = None
