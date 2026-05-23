from typing import List, Optional, Dict
from sqlmodel import SQLModel, Field


class StructuredPageCreate(SQLModel):
    raw_text: str = ""
    triplets: List[List[str]] = Field(default_factory=list)
    structured_at: Optional[float] = None


class StructuredPageUpdate(SQLModel):
    raw_text: Optional[str] = None
    triplets: Optional[List[List[str]]] = None
    structured_at: Optional[float] = None


class StructuredPageRead(SQLModel):
    id: str
    creation_timestamp: float
    raw_text: str
    triplets: List[List[str]]
    structured_at: float


class UnstructuredPageCreate(SQLModel):
    raw_text: str = ""
    predicted_output: str = ""
    prediction_error: float = 0.0


class UnstructuredPageUpdate(SQLModel):
    raw_text: Optional[str] = None
    predicted_output: Optional[str] = None
    prediction_error: Optional[float] = None


class UnstructuredPageRead(SQLModel):
    id: str
    creation_timestamp: float
    raw_text: str
    predicted_output: str
    prediction_error: float


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
