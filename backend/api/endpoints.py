# ==================== StructuredPage Endpoints ====================
import time
import uuid

from fastapi import Depends, Query, HTTPException
from sqlmodel import Session, select

from backend.api.api import app, get_session
from backend.api.api_data_schemas import (
    StructuredPageRead,
    StructuredPageCreate,
    StructuredPageUpdate,
    UnstructuredPageRead,
    UnstructuredPageCreate,
    UnstructuredPageUpdate,
    WikiPageRead,
    WikiPageCreate,
    WikiPageUpdate,
)
from backend.database.orm_schema import (
    StructuredPageModel,
    UnstructuredPageModel,
    WikiPageModel,
)


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


# ==================== Health Endpoints ====================


# Health check
@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
