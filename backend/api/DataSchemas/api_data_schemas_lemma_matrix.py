from sqlmodel import SQLModel
from pydantic import field_validator


class LemmaConnectionCreate(SQLModel):
    word1: str
    word2: str
    weight: int

    @field_validator("word1", "word2")
    @classmethod
    def words_not_empty(cls, v: str) -> str:
        """Validate that words are non-empty after stripping."""
        if not v or not v.strip():
            raise ValueError("word1 and word2 must not be empty or whitespace-only")
        return v

    @field_validator("weight")
    @classmethod
    def weight_non_negative(cls, v: int) -> int:
        """Validate that weight is a non-negative integer."""
        if v < 0:
            raise ValueError("weight must be non-negative (>= 0)")
        return v


class LemmaConnectionRead(SQLModel):
    id: int
    word1: str
    word2: str
    weight: int

class LemmaConnectionReadByKeyword(SQLModel):
    word1: str | None = None


class LemmaConnectionUpdate(SQLModel):
    word1: str | None = None
    word2: str | None = None
    weight: int | None = None
