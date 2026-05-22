from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, SQLModel, Field, select
from typing import Dict, List, Optional
import time
import uuid

from backend.database import  init_db
from backend.database.orm_schema import (
    StructuredPageModel,
    UnstructuredPageModel,
    WikiPageModel,
)

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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Executes prior to the first incoming request
    init_db.init_db()
    yield
    # Execute cleanup procedures here (e.g., engine disposal)


def get_session():
    if init_db.SessionLocal is None:
        init_db.init_db()
    session_factory = init_db.SessionLocal
    if session_factory is None:
        raise RuntimeError("SessionLocal is not initialized")
    with session_factory() as session:
        yield session


app = FastAPI(
    title="Pages API",
    description="FastAPI with SQLite for managing Pages",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,  # type: ignore
    allow_origins=["*"],  # type: ignore
    allow_credentials=True,  # type: ignore
    allow_methods=["*"],  # type: ignore
    allow_headers=["*"],  # type: ignore
)


# ==================== StructuredPage Endpoints ====================


@app.post(
    "/api/structured-pages",
    response_model=StructuredPageRead,
    tags=["StructuredPages"],
)
def create_structured_page(
    payload: StructuredPageCreate,
    session: Session = Depends(get_session),
):
    structured_page = StructuredPageModel(
        id=str(uuid.uuid4()),
        creation_timestamp=time.time(),
        raw_text=payload.raw_text,
        triplets=payload.triplets,
        structured_at=payload.structured_at or time.time(),
    )
    session.add(structured_page)
    session.commit()
    session.refresh(structured_page)
    return structured_page


@app.get(
    "/api/structured-pages",
    response_model=list[StructuredPageRead],
    tags=["StructuredPages"],
)
def get_all_structured_pages(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session),
):
    statement = select(StructuredPageModel).offset(skip).limit(limit)
    return session.exec(statement).all()


@app.get(
    "/api/structured-pages/{page_id}",
    response_model=StructuredPageRead,
    tags=["StructuredPages"],
)
def get_structured_page(page_id: str, session: Session = Depends(get_session)):
    structured_page = session.get(StructuredPageModel, page_id)
    if not structured_page:
        raise HTTPException(status_code=404, detail="Structured page not found")
    return structured_page


@app.put(
    "/api/structured-pages/{page_id}",
    response_model=StructuredPageRead,
    tags=["StructuredPages"],
)
def update_structured_page(
    page_id: str,
    payload: StructuredPageUpdate,
    session: Session = Depends(get_session),
):
    structured_page = session.get(StructuredPageModel, page_id)
    if not structured_page:
        raise HTTPException(status_code=404, detail="Structured page not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(structured_page, key, value)
    session.add(structured_page)
    session.commit()
    session.refresh(structured_page)
    return structured_page


# ==================== UnstructuredPage Endpoints ====================


@app.post(
    "/api/unstructured-pages",
    response_model=UnstructuredPageRead,
    tags=["UnstructuredPages"],
)
def create_unstructured_page(
    payload: UnstructuredPageCreate,
    session: Session = Depends(get_session),
):
    unstructured_page = UnstructuredPageModel(
        id=str(uuid.uuid4()),
        creation_timestamp=time.time(),
        raw_text=payload.raw_text,
        predicted_output=payload.predicted_output,
        prediction_error=payload.prediction_error,
    )
    session.add(unstructured_page)
    session.commit()
    session.refresh(unstructured_page)
    return unstructured_page


@app.get(
    "/api/unstructured-pages",
    response_model=list[UnstructuredPageRead],
    tags=["UnstructuredPages"],
)
def get_all_unstructured_pages(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session),
):
    statement = select(UnstructuredPageModel).offset(skip).limit(limit)
    return session.exec(statement).all()


@app.get(
    "/api/unstructured-pages/{page_id}",
    response_model=UnstructuredPageRead,
    tags=["UnstructuredPages"],
)
def get_unstructured_page(page_id: str, session: Session = Depends(get_session)):
    unstructured_page = session.get(UnstructuredPageModel, page_id)
    if not unstructured_page:
        raise HTTPException(status_code=404, detail="Unstructured page not found")
    return unstructured_page


@app.put(
    "/api/unstructured-pages/{page_id}",
    response_model=UnstructuredPageRead,
    tags=["UnstructuredPages"],
)
def update_unstructured_page(
    page_id: str,
    payload: UnstructuredPageUpdate,
    session: Session = Depends(get_session),
):
    unstructured_page = session.get(UnstructuredPageModel, page_id)
    if not unstructured_page:
        raise HTTPException(status_code=404, detail="Unstructured page not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(unstructured_page, key, value)
    session.add(unstructured_page)
    session.commit()
    session.refresh(unstructured_page)
    return unstructured_page


# ==================== WikiPage Endpoints ====================


@app.post("/api/wiki-pages", response_model=WikiPageRead, tags=["WikiPages"])
def create_wiki_page(
    payload: WikiPageCreate,
    session: Session = Depends(get_session),
):
    wiki_page = WikiPageModel(
        id=payload.id or str(uuid.uuid4()),
        version=payload.version,
        title=payload.title,
        body=payload.body,
        sections=payload.sections,
        categories=payload.categories,
        infobox=payload.infobox,
        wikilinks=payload.wikilinks,
        interwiki_links=payload.interwiki_links,
        external_links=payload.external_links,
        see_also=payload.see_also,
        references=payload.references,
        templates=payload.templates,
        disambiguation=payload.disambiguation,
        wikified_at=payload.wikified_at or time.time(),
    )
    session.add(wiki_page)
    session.commit()
    session.refresh(wiki_page)
    return wiki_page


@app.get("/api/wiki-pages", response_model=list[WikiPageRead], tags=["WikiPages"])
def get_all_wiki_pages(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session),
):
    statement = select(WikiPageModel).offset(skip).limit(limit)
    return session.exec(statement).all()


@app.get("/api/wiki-pages/{wiki_id}", response_model=WikiPageRead, tags=["WikiPages"])
def get_wiki_page(wiki_id: str, session: Session = Depends(get_session)):
    wiki_page = session.get(WikiPageModel, wiki_id)
    if not wiki_page:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    return wiki_page


@app.put("/api/wiki-pages/{wiki_id}", response_model=WikiPageRead, tags=["WikiPages"])
def update_wiki_page(
    wiki_id: str,
    payload: WikiPageUpdate,
    session: Session = Depends(get_session),
):
    wiki_page = session.get(WikiPageModel, wiki_id)
    if not wiki_page:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(wiki_page, key, value)
    session.add(wiki_page)
    session.commit()
    session.refresh(wiki_page)
    return wiki_page


# Health check
@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
