from typing import List, Optional
from sqlmodel import SQLModel, Field


# Schemas for Document / Lemma storage
class DocumentCreate(SQLModel):
	raw_text: str = ""
	# list of lemma tokens or keywords associated with the document
	lemmas: List[str] = Field(default_factory=list)
	# whether this document has been transformed into the matrix representation
	transformed_to_matrix: bool = False


class DocumentUpdate(SQLModel):
	raw_text: Optional[str] = None
	lemmas: Optional[List[str]] = None
	transformed_to_matrix: Optional[bool] = None


class DocumentRead(SQLModel):
	id: str
	timestamp: float
	raw_text: str
	lemmas: List[str]
	transformed_to_matrix: bool

