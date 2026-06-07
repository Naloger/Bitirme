from __future__ import annotations

from pydantic import BaseModel


class KeywordRecord(BaseModel):
	term: str
	count: int
	language: str | None = None
	language_model: str | None = None


class PpmiPairRecord(BaseModel):
	term_a: str
	term_b: str
	score: float
	language: str | None = None
	language_model: str | None = None


class KeywordsPayload(BaseModel):
	keywords: list[KeywordRecord]


class PpmiPayload(BaseModel):
	ppmi_pairs: list[PpmiPairRecord]

