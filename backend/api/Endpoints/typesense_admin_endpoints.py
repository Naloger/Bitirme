import os
import pathlib
import httpx
import logging
from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any, Optional

from Config.config import (
    TYPESENSE_HOST,
    TYPESENSE_PORT,
    TYPESENSE_API_KEY,
    TYPESENSE_EMBEDDING_PROVIDER,
    TYPESENSE_EMBEDDING_MODEL,
    TYPESENSE_EMBEDDING_DIMENSIONS,
    OLLAMA_HOST_URL
)
from backend.api import typesense_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Typesense Admin"])

TYPESENSE_URL = f"http://{TYPESENSE_HOST}:{TYPESENSE_PORT}"
HEADERS = {
    "X-TYPESENSE-API-KEY": TYPESENSE_API_KEY,
    "Content-Type": "application/json"
}

# --- Dashboard HTML Page serving ---

@router.get("/typesense-dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Serves the main Typesense admin visualization dashboard."""
    html_path = pathlib.Path(__file__).resolve().parent / "typesense_dashboard.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail=f"Dashboard template file not found at: {html_path}")
        
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

# --- Admin API Routes ---

@router.get("/api/typesense-admin/stats")
async def get_stats():
    """Checks the health of Typesense and Ollama, returning active configurations."""
    typesense_status = "error"
    ollama_status = "error"
    
    # 1. Check Typesense health
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{TYPESENSE_URL}/health", headers=HEADERS)
            if res.status_code == 200 and res.json().get("ok") is True:
                typesense_status = "ok"
    except (httpx.RequestError, httpx.HTTPStatusError):
        pass
        
    # 2. Check Ollama health
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{OLLAMA_HOST_URL}/api/tags")
            if res.status_code == 200:
                ollama_status = "ok"
    except (httpx.RequestError, httpx.HTTPStatusError):
        pass
        
    return {
        "typesense_status": typesense_status,
        "typesense_host": TYPESENSE_HOST,
        "typesense_port": TYPESENSE_PORT,
        "embedding_provider": TYPESENSE_EMBEDDING_PROVIDER,
        "embedding_model": TYPESENSE_EMBEDDING_MODEL,
        "embedding_dimensions": TYPESENSE_EMBEDDING_DIMENSIONS,
        "ollama_status": ollama_status,
        "ollama_host_url": OLLAMA_HOST_URL
    }

@router.get("/api/typesense-admin/collections")
async def list_collections():
    """Retrieves all collections and their metadata directly from Typesense."""
    url = f"{TYPESENSE_URL}/collections"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(url, headers=HEADERS)
            if res.status_code == 200:
                return res.json()
            else:
                raise HTTPException(status_code=res.status_code, detail=f"Typesense returned error: {res.text}")
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=500, detail=f"Failed to fetch collections: {exc}")

@router.get("/api/typesense-admin/collections/{name}/documents")
async def list_collection_documents(
    name: str = Path(..., description="Collection name"),
    q: str = Query("*", description="Search query string"),
    limit: int = Query(10, description="Max documents to return"),
    offset: int = Query(0, description="Documents offset page")
):
    """Paginates documents in a collection, supporting optional search."""
    # Determine columns to query by depending on collection type
    query_by = "subject,predicate,object,semantic_text"
    if name == "session_short_term_memory":
        query_by = "content,key,role"
        
    search_params = {
        "q": q,
        "query_by": query_by,
        "per_page": limit,
        "page": (offset // limit) + 1
    }
    
    try:
        results = await typesense_client.search_collection(name, search_params)
        documents = [hit["document"] for hit in results.get("hits", [])]
        total = results.get("found", 0)
        return {
            "documents": documents,
            "total": total
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents from '{name}': {exc}")

@router.get("/api/typesense-admin/collections/{name}/documents/{doc_id}")
async def get_collection_document(
    name: str = Path(..., description="Collection name"),
    doc_id: str = Path(..., description="Document ID")
):
    """Fetches a single document details by ID."""
    try:
        doc = await typesense_client.get_document(name, doc_id)
        return doc
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in '{name}'")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=exc)

@router.delete("/api/typesense-admin/collections/{name}/documents/{doc_id}")
async def delete_collection_document(
    name: str = Path(..., description="Collection name"),
    doc_id: str = Path(..., description="Document ID")
):
    """Deletes a single document by ID."""
    try:
        res = await typesense_client.delete_document(name, doc_id)
        return res
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in '{name}'")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=exc)

@router.delete("/api/typesense-admin/collections/{name}")
async def drop_collection(
    name: str = Path(..., description="Collection name to drop")
):
    """Drops a collection schema and deletes all its documents."""
    url = f"{TYPESENSE_URL}/collections/{name}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.delete(url, headers=HEADERS)
            if res.status_code == 200:
                return res.json()
            else:
                raise HTTPException(status_code=res.status_code, detail=f"Failed to drop collection '{name}': {res.text}")
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=500, detail=f"Failed to drop collection: {exc}")
