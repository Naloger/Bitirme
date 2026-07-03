import time
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Path, Query, HTTPException, status

from backend.api import typesense_client
from backend.api.DataSchemas.api_data_schemas_session import (
    RDFQuadCreate,
    RDFQuadRead,
    ShortTermMemoryCreate,
    ShortTermMemoryRead,
    SearchQuery,
    SearchResponse,
    SearchResultItem,
)

router = APIRouter(prefix="/api/session", tags=["SegmentedSessionStorage"])

# --- Helper Functions ---

def build_filter_by(session_id: str, custom_filter: Optional[str] = None) -> str:
    """Builds the filter_by query for Typesense ensuring session isolation."""
    base_filter = f"session_id:={session_id}"
    if custom_filter:
        return f"{base_filter} && ({custom_filter})"
    return base_filter

def format_search_results(typesense_response: Dict[str, Any]) -> SearchResponse:
    """Formats raw Typesense search results into the SearchResponse schema."""
    hits = []
    for hit in typesense_response.get("hits", []):
        hits.append(
            SearchResultItem(
                document=hit.get("document", {}),
                highlight=hit.get("highlight", {}),
                text_match=hit.get("text_match"),
                vector_distance=hit.get("vector_distance"),
            )
        )
    return SearchResponse(
        found=typesense_response.get("found", 0),
        took_ms=typesense_response.get("search_time_ms", 0),
        hits=hits,
    )

# ==================== EGO SEGMENT ENDPOINTS ====================

@router.post(
    "/{session_id}/ego",
    response_model=RDFQuadRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a single RDF quad to the Ego segment",
    description="Inserts a subject-predicate-object quad with optional context and embedding into the ego segment.",
)
async def add_ego_quad(
    payload: RDFQuadCreate,
    session_id: str = Path(..., description="The unique session identifier"),
):
    doc_id = payload.id or str(uuid.uuid4())
    doc: Dict[str, Any] = {
        "id": doc_id,
        "session_id": session_id,
        "subject": payload.subject,
        "predicate": payload.predicate,
        "object": payload.object,
        "context": payload.context or "",
        "semantic_text": payload.semantic_text or f"{payload.subject} {payload.predicate} {payload.object}",
        "timestamp": int(time.time()),
    }
    if payload.embedding:
        doc["embedding"] = payload.embedding
        
    try:
        result = await typesense_client.index_document("session_ego", doc)
        return RDFQuadRead(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store RDF quad in ego: {exc}"
        )

@router.post(
    "/{session_id}/ego/bulk",
    response_model=List[RDFQuadRead],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk add RDF quads to the Ego segment",
    description="Efficiently loads multiple RDF quads into the ego segment.",
)
async def bulk_add_ego_quads(
    payload: List[RDFQuadCreate],
    session_id: str = Path(..., description="The unique session identifier"),
):
    if not payload:
        return []
        
    docs = []
    t_now = int(time.time())
    for item in payload:
        doc_id = item.id or str(uuid.uuid4())
        doc: Dict[str, Any] = {
            "id": doc_id,
            "session_id": session_id,
            "subject": item.subject,
            "predicate": item.predicate,
            "object": item.object,
            "context": item.context or "",
            "semantic_text": item.semantic_text or f"{item.subject} {item.predicate} {item.object}",
            "timestamp": t_now,
        }
        if item.embedding:
            doc["embedding"] = item.embedding
        docs.append(doc)
        
    try:
        import_results = await typesense_client.bulk_index_documents("session_ego", docs)
        # Check for errors in bulk import results
        errors = [res for res in import_results if not res.get("success", True)]
        if errors:
            raise HTTPException(
                status_code=400,
                detail=f"Some RDF quads failed to import: {errors[:5]}"
            )
        
        # Return imported items
        return [RDFQuadRead(**doc) for doc in docs]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed bulk import of RDF quads in ego: {exc}"
        )

@router.get(
    "/{session_id}/ego",
    response_model=List[RDFQuadRead],
    summary="List RDF quads in the Ego segment",
    description="Performs a GET query on the ego segment. Highly filterable and segregates session data.",
)
async def list_ego_quads(
    session_id: str = Path(..., description="The unique session identifier"),
    q: str = Query("*", description="Search query string"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    predicate: Optional[str] = Query(None, description="Filter by predicate"),
    object_filter: Optional[str] = Query(None, alias="object", description="Filter by object"),
    context: Optional[str] = Query(None, description="Filter by context"),
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
):
    filters = []
    if subject:
        filters.append(f"subject:={subject}")
    if predicate:
        filters.append(f"predicate:={predicate}")
    if object_filter:
        filters.append(f"object:={object_filter}")
    if context:
        filters.append(f"context:={context}")
        
    custom_filter = " && ".join(filters) if filters else None
    filter_by = build_filter_by(session_id, custom_filter)
    
    search_params = {
        "q": q,
        "query_by": "semantic_text,subject,predicate,object,context",
        "filter_by": filter_by,
        "per_page": limit,
        "page": (offset // limit) + 1,
        "sort_by": "timestamp:desc"
    }
    
    try:
        results = await typesense_client.search_collection("session_ego", search_params)
        return [RDFQuadRead(**hit["document"]) for hit in results.get("hits", [])]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query ego: {exc}"
        )

@router.post(
    "/{session_id}/ego/search",
    response_model=SearchResponse,
    summary="Hybrid Vector & Lexical Search on Ego segment",
    description="Runs advanced search including vector/nearest-neighbor search on the ego segment.",
)
async def search_ego_quads(
    query: SearchQuery,
    session_id: str = Path(..., description="The unique session identifier"),
):
    filter_by = build_filter_by(session_id, query.filter_by)
    search_params = {
        "q": query.q,
        "query_by": query.query_by or "semantic_text,subject,predicate,object,context",
        "filter_by": filter_by,
        "per_page": query.limit,
        "page": (query.offset // query.limit) + 1,
    }
    
    if query.vector:
        search_params["vector_query"] = f"embedding:([{','.join(map(str, query.vector))}], k:{query.limit})"
        
    try:
        results = await typesense_client.search_collection("session_ego", search_params)
        return format_search_results(results)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ego search query failed: {exc}"
        )

@router.delete(
    "/{session_id}/ego",
    summary="Clear all Ego data for this session",
    description="Deletes all RDF quads belonging to this session in the ego segment.",
)
async def clear_ego(
    session_id: str = Path(..., description="The unique session identifier"),
):
    try:
        result = await typesense_client.delete_documents_by_query("session_ego", f"session_id:={session_id}")
        return {"status": "success", "deleted_count": result.get("num_deleted", 0)}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear ego segment: {exc}"
        )

@router.delete(
    "/{session_id}/ego/{doc_id}",
    summary="Delete a specific RDF quad from Ego",
    description="Deletes a single RDF quad from the ego segment by document ID.",
)
async def delete_ego_quad(
    session_id: str = Path(..., description="The unique session identifier"),
    doc_id: str = Path(..., description="The unique document identifier to delete"),
):
    try:
        # First verify it belongs to this session to avoid cross-tenant delete exploits
        doc = await typesense_client.get_document("session_ego", doc_id)
        if doc.get("session_id") != session_id:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized: document does not belong to this session"
            )
            
        await typesense_client.delete_document("session_ego", doc_id)
        return {"status": "success", "id": doc_id}
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete RDF quad: {exc}"
        )


# ==================== WORKING MEMORY SEGMENT ENDPOINTS ====================

@router.post(
    "/{session_id}/working-memory",
    response_model=RDFQuadRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a single RDF quad to the Working Memory segment",
    description="Inserts a subject-predicate-object quad with optional context and embedding into the working memory segment.",
)
async def add_working_memory_quad(
    payload: RDFQuadCreate,
    session_id: str = Path(..., description="The unique session identifier"),
):
    doc_id = payload.id or str(uuid.uuid4())
    doc: Dict[str, Any] = {
        "id": doc_id,
        "session_id": session_id,
        "subject": payload.subject,
        "predicate": payload.predicate,
        "object": payload.object,
        "context": payload.context or "",
        "semantic_text": payload.semantic_text or f"{payload.subject} {payload.predicate} {payload.object}",
        "timestamp": int(time.time()),
    }
    if payload.embedding:
        doc["embedding"] = payload.embedding
        
    try:
        result = await typesense_client.index_document("session_working_memory", doc)
        return RDFQuadRead(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store RDF quad in working memory: {exc}"
        )

@router.post(
    "/{session_id}/working-memory/bulk",
    response_model=List[RDFQuadRead],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk add RDF quads to the Working Memory segment",
    description="Efficiently loads multiple RDF quads into the working memory segment.",
)
async def bulk_add_working_memory_quads(
    payload: List[RDFQuadCreate],
    session_id: str = Path(..., description="The unique session identifier"),
):
    if not payload:
        return []
        
    docs = []
    t_now = int(time.time())
    for item in payload:
        doc_id = item.id or str(uuid.uuid4())
        doc: Dict[str, Any] = {
            "id": doc_id,
            "session_id": session_id,
            "subject": item.subject,
            "predicate": item.predicate,
            "object": item.object,
            "context": item.context or "",
            "semantic_text": item.semantic_text or f"{item.subject} {item.predicate} {item.object}",
            "timestamp": t_now,
        }
        if item.embedding:
            doc["embedding"] = item.embedding
        docs.append(doc)
        
    try:
        import_results = await typesense_client.bulk_index_documents("session_working_memory", docs)
        errors = [res for res in import_results if not res.get("success", True)]
        if errors:
            raise HTTPException(
                status_code=400,
                detail=f"Some RDF quads failed to import: {errors[:5]}"
            )
        return [RDFQuadRead(**doc) for doc in docs]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed bulk import of RDF quads in working memory: {exc}"
        )

@router.get(
    "/{session_id}/working-memory",
    response_model=List[RDFQuadRead],
    summary="List RDF quads in the Working Memory segment",
    description="Performs a GET query on the working memory segment. Highly filterable and segregates session data.",
)
async def list_working_memory_quads(
    session_id: str = Path(..., description="The unique session identifier"),
    q: str = Query("*", description="Search query string"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    predicate: Optional[str] = Query(None, description="Filter by predicate"),
    object_filter: Optional[str] = Query(None, alias="object", description="Filter by object"),
    context: Optional[str] = Query(None, description="Filter by context"),
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
):
    filters = []
    if subject:
        filters.append(f"subject:={subject}")
    if predicate:
        filters.append(f"predicate:={predicate}")
    if object_filter:
        filters.append(f"object:={object_filter}")
    if context:
        filters.append(f"context:={context}")
        
    custom_filter = " && ".join(filters) if filters else None
    filter_by = build_filter_by(session_id, custom_filter)
    
    search_params = {
        "q": q,
        "query_by": "semantic_text,subject,predicate,object,context",
        "filter_by": filter_by,
        "per_page": limit,
        "page": (offset // limit) + 1,
        "sort_by": "timestamp:desc"
    }
    
    try:
        results = await typesense_client.search_collection("session_working_memory", search_params)
        return [RDFQuadRead(**hit["document"]) for hit in results.get("hits", [])]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query working memory: {exc}"
        )

@router.post(
    "/{session_id}/working-memory/search",
    response_model=SearchResponse,
    summary="Hybrid Vector & Lexical Search on Working Memory segment",
    description="Runs advanced search including vector/nearest-neighbor search on the working memory segment.",
)
async def search_working_memory_quads(
    query: SearchQuery,
    session_id: str = Path(..., description="The unique session identifier"),
):
    filter_by = build_filter_by(session_id, query.filter_by)
    search_params = {
        "q": query.q,
        "query_by": query.query_by or "semantic_text,subject,predicate,object,context",
        "filter_by": filter_by,
        "per_page": query.limit,
        "page": (query.offset // query.limit) + 1,
    }
    
    if query.vector:
        search_params["vector_query"] = f"embedding:([{','.join(map(str, query.vector))}], k:{query.limit})"
        
    try:
        results = await typesense_client.search_collection("session_working_memory", search_params)
        return format_search_results(results)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Working memory search query failed: {exc}"
        )

@router.delete(
    "/{session_id}/working-memory",
    summary="Clear all Working Memory data for this session",
    description="Deletes all RDF quads belonging to this session in the working memory segment.",
)
async def clear_working_memory(
    session_id: str = Path(..., description="The unique session identifier"),
):
    try:
        result = await typesense_client.delete_documents_by_query("session_working_memory", f"session_id:={session_id}")
        return {"status": "success", "deleted_count": result.get("num_deleted", 0)}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear working memory segment: {exc}"
        )

@router.delete(
    "/{session_id}/working-memory/{doc_id}",
    summary="Delete a specific RDF quad from Working Memory",
    description="Deletes a single RDF quad from the working memory segment by document ID.",
)
async def delete_working_memory_quad(
    session_id: str = Path(..., description="The unique session identifier"),
    doc_id: str = Path(..., description="The unique document identifier to delete"),
):
    try:
        # First verify it belongs to this session to avoid cross-tenant delete exploits
        doc = await typesense_client.get_document("session_working_memory", doc_id)
        if doc.get("session_id") != session_id:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized: document does not belong to this session"
            )
            
        await typesense_client.delete_document("session_working_memory", doc_id)
        return {"status": "success", "id": doc_id}
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete RDF quad: {exc}"
        )


# ==================== SHORT-TERM MEMORY ENDPOINTS ====================

@router.post(
    "/{session_id}/short-term-memory",
    response_model=ShortTermMemoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a standard session record to Short-Term Memory",
    description="Inserts a generic session memory block with optional key/role and vector embedding.",
)
async def add_short_term_memory(
    payload: ShortTermMemoryCreate,
    session_id: str = Path(..., description="The unique session identifier"),
):
    doc_id = payload.id or str(uuid.uuid4())
    doc: Dict[str, Any] = {
        "id": doc_id,
        "session_id": session_id,
        "key": payload.key or "",
        "content": payload.content,
        "role": payload.role or "",
        "timestamp": int(time.time()),
    }
    if payload.embedding:
        doc["embedding"] = payload.embedding
        
    try:
        result = await typesense_client.index_document("session_short_term_memory", doc)
        return ShortTermMemoryRead(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store memory block in short-term memory: {exc}"
        )

@router.post(
    "/{session_id}/short-term-memory/bulk",
    response_model=List[ShortTermMemoryRead],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk add memory records to Short-Term Memory",
    description="Bulk imports standard session memory records.",
)
async def bulk_add_short_term_memory(
    payload: List[ShortTermMemoryCreate],
    session_id: str = Path(..., description="The unique session identifier"),
):
    if not payload:
        return []
        
    docs = []
    t_now = int(time.time())
    for item in payload:
        doc_id = item.id or str(uuid.uuid4())
        doc: Dict[str, Any] = {
            "id": doc_id,
            "session_id": session_id,
            "key": item.key or "",
            "content": item.content,
            "role": item.role or "",
            "timestamp": t_now,
        }
        if item.embedding:
            doc["embedding"] = item.embedding
        docs.append(doc)
        
    try:
        import_results = await typesense_client.bulk_index_documents("session_short_term_memory", docs)
        errors = [res for res in import_results if not res.get("success", True)]
        if errors:
            raise HTTPException(
                status_code=400,
                detail=f"Some memory items failed to import: {errors[:5]}"
            )
        return [ShortTermMemoryRead(**doc) for doc in docs]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed bulk import of short-term memories: {exc}"
        )

@router.get(
    "/{session_id}/short-term-memory",
    response_model=List[ShortTermMemoryRead],
    summary="List standard session records from Short-Term Memory",
    description="Performs a GET query on the short term memory segment. Highly filterable and segregates session data.",
)
async def list_short_term_memory(
    session_id: str = Path(..., description="The unique session identifier"),
    q: str = Query("*", description="Search query string"),
    key: Optional[str] = Query(None, description="Filter by key"),
    role: Optional[str] = Query(None, description="Filter by role"),
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
):
    filters = []
    if key:
        filters.append(f"key:={key}")
    if role:
        filters.append(f"role:={role}")
        
    custom_filter = " && ".join(filters) if filters else None
    filter_by = build_filter_by(session_id, custom_filter)
    
    search_params = {
        "q": q,
        "query_by": "key,content,role",
        "filter_by": filter_by,
        "per_page": limit,
        "page": (offset // limit) + 1,
        "sort_by": "timestamp:desc"
    }
    
    try:
        results = await typesense_client.search_collection("session_short_term_memory", search_params)
        return [ShortTermMemoryRead(**hit["document"]) for hit in results.get("hits", [])]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query short-term memory: {exc}"
        )

@router.post(
    "/{session_id}/short-term-memory/search",
    response_model=SearchResponse,
    summary="Hybrid Vector & Lexical Search on Short-Term Memory",
    description="Runs advanced search including vector/nearest-neighbor search on the short-term memory segment.",
)
async def search_short_term_memory(
    query: SearchQuery,
    session_id: str = Path(..., description="The unique session identifier"),
):
    filter_by = build_filter_by(session_id, query.filter_by)
    search_params = {
        "q": query.q,
        "query_by": query.query_by or "key,content,role",
        "filter_by": filter_by,
        "per_page": query.limit,
        "page": (query.offset // query.limit) + 1,
    }
    
    if query.vector:
        search_params["vector_query"] = f"embedding:([{','.join(map(str, query.vector))}], k:{query.limit})"
        
    try:
        results = await typesense_client.search_collection("session_short_term_memory", search_params)
        return format_search_results(results)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Short-term memory search query failed: {exc}"
        )

@router.delete(
    "/{session_id}/short-term-memory",
    summary="Clear all Short-Term Memory for this session",
    description="Deletes all standard memory records belonging to this session in the short-term memory segment.",
)
async def clear_short_term_memory(
    session_id: str = Path(..., description="The unique session identifier"),
):
    try:
        result = await typesense_client.delete_documents_by_query("session_short_term_memory", f"session_id:={session_id}")
        return {"status": "success", "deleted_count": result.get("num_deleted", 0)}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear short-term memory segment: {exc}"
        )

@router.delete(
    "/{session_id}/short-term-memory/{doc_id}",
    summary="Delete a specific record from Short-Term Memory",
    description="Deletes a single standard memory record from the short-term memory segment by document ID.",
)
async def delete_short_term_memory(
    session_id: str = Path(..., description="The unique session identifier"),
    doc_id: str = Path(..., description="The unique document identifier to delete"),
):
    try:
        # First verify it belongs to this session to avoid cross-tenant delete exploits
        doc = await typesense_client.get_document("session_short_term_memory", doc_id)
        if doc.get("session_id") != session_id:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized: document does not belong to this session"
            )
            
        await typesense_client.delete_document("session_short_term_memory", doc_id)
        return {"status": "success", "id": doc_id}
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete short-term memory record: {exc}"
        )
