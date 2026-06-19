from sqlmodel import SQLModel


class LemmaConnectionCreate(SQLModel):
    word1: str
    word2: str
    weight: int


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
