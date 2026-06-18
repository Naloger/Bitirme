from sqlmodel import SQLModel


class LemmaConnectionCreate(SQLModel):
    owner_id: int | None = None
    word1: str
    word2: str
    weight: int


class LemmaConnectionRead(SQLModel):
    id: int
    owner_id: int
    word1: str
    word2: str
    weight: int

class LemmaConnectionReadByKeyword(SQLModel):
    owner_id: int | None = None
    word1: str | None = None


class LemmaConnectionUpdate(SQLModel):
    owner_id: int | None = None
    word1: str | None = None
    word2: str | None = None
    weight: int | None = None
