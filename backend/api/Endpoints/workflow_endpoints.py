import time
import uuid
import re
import hashlib
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlmodel import Session

from backend.api.api_init import get_session, get_lemma_matrix_session
from backend.api import typesense_client
from backend.database.ORMSchemas.orm_schema_pages import UnstructuredPageModel
from Libs.Lemmatizer.lemma_matrix import LemmaMatrixBuilder
from Libs.Leiden.leiden_spreading_activation import spreading_activation
from Scripts.infra.age.rdf_quadstore import RDFQuadstore
from Config.config import AGE_MEMORY_DB, AGE_RDF_GRAPH

router = APIRouter(tags=["Workflow"])


class RawInputPayload(BaseModel):
    raw_text: str = Field(..., description="The raw unstructured text input")
    session_id: Optional[str] = Field(None, description="The session identifier. If not provided, a random UUID will be generated.")
    key: Optional[str] = Field(None, description="Optional key to associate with Typesense short term memory")
    role: Optional[str] = Field(None, description="Optional role to associate with Typesense short term memory")


class RawInputWorkflowResponse(BaseModel):
    status: str
    session_id: str
    unstructured_page_id: str
    lemmas: List[str]
    extended_keywords: List[str]
    saved_quads_count: int


def _clean_text_to_json_safe(text: str) -> str:
    """Clean input text to be JSON-acceptable by:
    1. Removing control characters (ASCII 0-31 except space, tab, newline, CR).
    2. Stripping double quotes and backslashes.
    3. Replacing newlines, carriage returns, and tabs with space.
    4. Removing zero-width spaces and other non-printable unicode control characters.
    5. Normalizing multiple spaces to a single space.
    """
    # Remove unicode control characters and zero-width characters
    text = re.sub(r'[\u200b-\u200d\ufeff]', '', text)
    
    # Strip control characters (ASCII 0-31)
    text = "".join(ch for ch in text if ord(ch) >= 32 or ch in "\n\r\t")
    
    cleaned = text.replace('"', '').replace('\\', '').replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    return re.sub(r'\s+', ' ', cleaned).strip()


@router.post(
    "/api/workflow/raw-input",
    response_model=RawInputWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Process raw input cleanly across Page DB, Typesense, and Apache AGE",
    description=(
        "1. Stores the raw text in the page DB unstructured table (filling non-prediction fields).\n"
        "2. Indexes the raw text in Typesense short-term memory.\n"
        "3. Cleans, normalizes, and lemmatizes the raw text.\n"
        "4. Runs spreading activation to get extended keywords.\n"
        "5. Queries Apache AGE for matching quads and stores them in Typesense working memory."
    ),
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "raw_text": {"type": "string", "example": "The sun is a roman god."},
                            "session_id": {"type": "string", "example": "test-session-123"},
                            "key": {"type": "string", "example": "test-key"},
                            "role": {"type": "string", "example": "user"}
                        },
                        "required": ["raw_text"]
                    }
                }
            }
        }
    }
)
async def process_raw_input(
    request: Request,
    page_db: Session = Depends(get_session),
    lemma_db: Session = Depends(get_lemma_matrix_session),
):
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8").strip()

    raw_text = ""
    session_id = None
    key = None
    role = None

    # Try standard JSON parsing first
    try:
        import json
        payload_dict = json.loads(body_str)
        raw_text = payload_dict.get("raw_text", "")
        session_id = payload_dict.get("session_id")
        key = payload_dict.get("key")
        role = payload_dict.get("role")
    except Exception:
        # Lenient fallback parsing for malformed JSON
        parsed = {}
        fields = ["raw_text", "session_id", "key", "role"]
        positions = []
        for field in fields:
            match = re.search(r'"' + field + r'"\s*:', body_str)
            if match:
                positions.append((match.start(), field, match.end()))
        
        positions.sort()
        for i, (start, field, end) in enumerate(positions):
            val_start_idx = body_str.find('"', end)
            if val_start_idx == -1:
                continue
            val_start_idx += 1
            
            if i + 1 < len(positions):
                val_end_limit = positions[i + 1][0]
            else:
                val_end_limit = len(body_str)
                
            val_sub = body_str[val_start_idx:val_end_limit].strip()
            if val_sub.endswith("}"):
                val_sub = val_sub[:-1].strip()
            if val_sub.endswith(","):
                val_sub = val_sub[:-1].strip()
            if val_sub.endswith('"'):
                val_sub = val_sub[:-1]
                
            parsed[field] = val_sub

        raw_text = parsed.get("raw_text", "")
        session_id = parsed.get("session_id")
        key = parsed.get("key")
        role = parsed.get("role")

    # If still no raw_text found (e.g., if body is just plain text, not JSON at all)
    if not raw_text:
        # Check if the body looks like JSON. If not, treat the whole body as raw_text
        if not (body_str.startswith("{") or body_str.startswith("[")):
            raw_text = body_str
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not find 'raw_text' field in payload."
            )

    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must contain a non-empty 'raw_text'."
        )

    session_id = session_id or str(uuid.uuid4())
    
    # 1. Clean, normalize, and lemmatize input to get lemmas list
    try:
        cleaned_text = _clean_text_to_json_safe(raw_text)
        builder = LemmaMatrixBuilder()
        lemmas = builder.tokenize(cleaned_text)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to lemmatize raw text: {exc}"
        )

    # 2. Page DB: fill possible to fill fields in unstructured table (dont fill prediction fields)
    unstructured_page_id = str(uuid.uuid4())
    try:
        unstructured_page = UnstructuredPageModel(
            id=unstructured_page_id,
            creation_timestamp=time.time(),
            raw_text=raw_text,
            predicted_output="",
            prediction_error=0.0,
            transformed_to_matrix=False,
            lemmatized_words=lemmas,
        )
        page_db.add(unstructured_page)
        page_db.commit()
    except Exception as exc:
        page_db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save unstructured page to database: {exc}"
        )

    # 3. Typesense: input gets stored in collection short term memory
    stm_id = str(uuid.uuid4())
    stm_doc = {
        "id": stm_id,
        "session_id": session_id,
        "key": key or "",
        "content": raw_text,
        "role": role or "user",
        "timestamp": int(time.time()),
    }
    try:
        await typesense_client.index_document("session_short_term_memory", stm_doc)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to index document in Typesense short-term memory: {exc}"
        )

    # 4. Spreading activation: get the spread activation extended keyword list
    try:
        scores = spreading_activation(
            session=lemma_db,
            seed_words=lemmas,
            decay=0.8,
            firing_threshold=0.01,
            max_steps=5,
        )
        extended_keywords = list(scores.keys())
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Spreading activation failed: {exc}"
        )

    # 5. Apache AGE: Query Apache AGE DB with the extended keyword list and save to working memory Typesense collection
    search_terms = list(set(lemmas + extended_keywords))
    saved_quads_count = 0
    
    if search_terms:
        try:
            store = RDFQuadstore(db_name=AGE_MEMORY_DB, graph_name=AGE_RDF_GRAPH)
            
            # Fetch quads belonging to the current session or global/default contexts
            session_quads = store.query_quads(context=session_id)
            default_quads = store.query_quads(context="default")
            global_quads = store.query_quads(context="")
            
            # Combine and deduplicate quads in memory
            seen_quads = set()
            all_quads = []
            for q in (session_quads + default_quads + global_quads):
                sub = q.get("subject", {}).get("value", "")
                pred = q.get("predicate", "")
                obj = q.get("object", {}).get("value", "")
                ctx = q.get("context", "") or ""
                q_key = (sub, pred, obj, ctx)
                if q_key not in seen_quads:
                    seen_quads.add(q_key)
                    all_quads.append(q)
            
            matched_quads = []
            for quad in all_quads:
                s_val = str(quad.get("subject", {}).get("value", "")).lower()
                p_val = str(quad.get("predicate", "")).lower()
                o_val = str(quad.get("object", {}).get("value", "")).lower()
                
                match_found = False
                for term in search_terms:
                    term_lower = term.lower().strip()
                    if not term_lower:
                        continue
                    if term_lower in s_val or term_lower in p_val or term_lower in o_val:
                        match_found = True
                        break
                        
                if match_found:
                    matched_quads.append(quad)
            
            if matched_quads:
                wm_docs = []
                for quad in matched_quads:
                    subject = quad.get("subject", {}).get("value", "")
                    predicate = quad.get("predicate", "")
                    obj = quad.get("object", {}).get("value", "")
                    ctx = quad.get("context", "") or ""
                    
                    if not subject or not predicate or not obj:
                        continue
                        
                    # Generate a unique deterministic ID to prevent duplicate records in Typesense
                    id_raw = f"{session_id}_{subject}_{predicate}_{obj}"
                    doc_id = hashlib.md5(id_raw.encode("utf-8")).hexdigest()
                    
                    doc = {
                        "id": doc_id,
                        "session_id": session_id,
                        "subject": subject,
                        "predicate": predicate,
                        "object": obj,
                        "context": ctx,
                        "semantic_text": f"{subject} {predicate} {obj}",
                        "timestamp": int(time.time()),
                    }
                    wm_docs.append(doc)
                
                if wm_docs:
                    await typesense_client.bulk_index_documents("session_working_memory", wm_docs)
                    saved_quads_count = len(wm_docs)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to query Apache AGE or save to Typesense working memory: {exc}"
            )

    return RawInputWorkflowResponse(
        status="success",
        session_id=session_id,
        unstructured_page_id=unstructured_page_id,
        lemmas=lemmas,
        extended_keywords=extended_keywords,
        saved_quads_count=saved_quads_count,
    )
