from typing import List, Optional, Dict
from sqlmodel import SQLModel, Field


# ==================== Page  ====================

class StructuredPageCreate(SQLModel):
    unstructured_page_id: int
    # each triplet is expected to be [str, int, str]
    keywords: List[str] = Field(default_factory=list)
    structured_at: Optional[float] = None
    transformed_to_graph: bool = False

class StructuredPageUpdate(SQLModel):
    unstructured_page_id: int = None
    keywords: Optional[List[str]] = None
    structured_at: Optional[float] = None
    transformed_to_graph: Optional[bool] = None

class StructuredPageRead(SQLModel):
    id: str
    creation_timestamp: float
    unstructured_page_id: int
    keywords: List[str]
    structured_at: float
    transformed_to_graph: bool

class UnstructuredPageCreate(SQLModel):
    raw_text: str = ""
    predicted_output: str = ""
    prediction_error: float = 0.0
    transformed_to_matrix: bool = False


class UnstructuredPageUpdate(SQLModel):
    raw_text: Optional[str] = None
    predicted_output: Optional[str] = None
    prediction_error: Optional[float] = None
    transformed_to_matrix: Optional[bool] = None

class UnstructuredPageRead(SQLModel):
    id: str
    creation_timestamp: float
    raw_text: str
    predicted_output: str
    prediction_error: float
    transformed_to_matrix: bool


class WikiPageCreate(SQLModel):
    id: Optional[str] = None
    version: int = 1
    title: str = ""
    body: str = ""
    sections: List[Dict[str, str]] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    infobox: Dict[str, str] = Field(default_factory=dict)
    wikilinks: List[str] = Field(default_factory=list)
    interwiki_links: Dict[str, str] = Field(default_factory=dict)
    external_links: List[Dict[str, str]] = Field(default_factory=list)
    see_also: List[str] = Field(default_factory=list)
    references: List[Dict[str, str]] = Field(default_factory=list)
    templates: List[str] = Field(default_factory=list)
    disambiguation: List[str] = Field(default_factory=list)
    wikified_at: Optional[float] = None


class WikiPageUpdate(SQLModel):
    version: Optional[int] = None
    title: Optional[str] = None
    body: Optional[str] = None
    sections: Optional[List[Dict[str, str]]] = None
    categories: Optional[List[str]] = None
    infobox: Optional[Dict[str, str]] = None
    wikilinks: Optional[List[str]] = None
    interwiki_links: Optional[Dict[str, str]] = None
    external_links: Optional[List[Dict[str, str]]] = None
    see_also: Optional[List[str]] = None
    references: Optional[List[Dict[str, str]]] = None
    templates: Optional[List[str]] = None
    disambiguation: Optional[List[str]] = None
    wikified_at: Optional[float] = None


class WikiPageRead(SQLModel):
    id: str
    version: int
    title: str
    body: str
    sections: List[Dict[str, str]]
    categories: List[str]
    infobox: Dict[str, str]
    wikilinks: List[str]
    interwiki_links: Dict[str, str]
    external_links: List[Dict[str, str]]
    see_also: List[str]
    references: List[Dict[str, str]]
    templates: List[str]
    disambiguation: List[str]
    wikified_at: float

# ==================== Keyword  ====================
