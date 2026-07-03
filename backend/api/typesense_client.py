import logging
import httpx
import json
from typing import List, Dict, Any
from Config.config import (
    TYPESENSE_HOST,
    TYPESENSE_PORT,
    TYPESENSE_API_KEY,
    TYPESENSE_EMBEDDING_PROVIDER,
    TYPESENSE_EMBEDDING_MODEL,
    TYPESENSE_EMBEDDING_DIMENSIONS,
    OLLAMA_HOST_URL
)

logger = logging.getLogger(__name__)

TYPESENSE_URL = f"http://{TYPESENSE_HOST}:{TYPESENSE_PORT}"
HEADERS = {
    "X-TYPESENSE-API-KEY": TYPESENSE_API_KEY,
    "Content-Type": "application/json"
}

def get_embedding_field_definition() -> Dict[str, Any]:
    """Generates a Typesense embedding field definition based on config settings.
    We return a simple float[] definition since embeddings are computed at the application level.
    """
    return {
        "name": "embedding",
        "type": "float[]",
        "optional": True,
        "num_dim": TYPESENSE_EMBEDDING_DIMENSIONS
    }

async def check_and_create_collection(client: httpx.AsyncClient, schema: Dict[str, Any]) -> None:
    collection_name = schema["name"]
    check_url = f"{TYPESENSE_URL}/collections/{collection_name}"
    
    try:
        response = await client.get(check_url, headers=HEADERS)
        if response.status_code == 200:
            logger.info(f"Typesense collection '{collection_name}' already exists.")
            return
        elif response.status_code == 404:
            logger.info(f"Typesense collection '{collection_name}' not found. Creating...")
            create_url = f"{TYPESENSE_URL}/collections"
            create_response = await client.post(create_url, headers=HEADERS, json=schema)
            if create_response.status_code in (200, 201):
                logger.info(f"Successfully created Typesense collection '{collection_name}'.")
            else:
                logger.error(f"Failed to create collection '{collection_name}': {create_response.status_code} - {create_response.text}")
        else:
            logger.error(f"Unexpected response when checking collection '{collection_name}': {response.status_code} - {response.text}")
    except Exception as exc:
        logger.error(f"Error connecting to Typesense to initialize '{collection_name}': {exc}")

async def ensure_ollama_model_pulled() -> None:
    """Attempts to pull the configured model from Ollama if using Ollama provider."""
    if TYPESENSE_EMBEDDING_PROVIDER != "ollama":
        return
        
    model_name = TYPESENSE_EMBEDDING_MODEL
    if model_name.startswith("ollama/"):
        model_name = model_name.replace("ollama/", "", 1)
    elif model_name.startswith("openai/"):
        model_name = model_name.replace("openai/", "", 1)
    elif model_name.startswith("ts/"):
        model_name = model_name.replace("ts/", "", 1)
        
    pull_url = f"{OLLAMA_HOST_URL}/api/pull"
    logger.info(f"Ollama provider active. Ensuring model '{model_name}' is pulled locally via {pull_url}...")
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(pull_url, json={"name": model_name, "stream": False})
            if response.status_code == 200:
                logger.info(f"Successfully pulled/verified Ollama model '{model_name}'.")
            else:
                logger.warning(f"Ollama server returned status {response.status_code} during model pull: {response.text}")
    except Exception as exc:
        logger.warning(f"Failed to pull Ollama model '{model_name}' (ensure Ollama is running at {OLLAMA_HOST_URL}): {exc}")

async def get_ollama_embedding(text: str) -> List[float]:
    """Generates embeddings using the local Ollama instance on the host."""
    url = f"{OLLAMA_HOST_URL}/api/embeddings"
    model_name = TYPESENSE_EMBEDDING_MODEL
    # Strip any prefix
    if model_name.startswith("ollama/"):
        model_name = model_name.replace("ollama/", "", 1)
    elif model_name.startswith("openai/"):
        model_name = model_name.replace("openai/", "", 1)
    elif model_name.startswith("ts/"):
        model_name = model_name.replace("ts/", "", 1)
        
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json={"model": model_name, "prompt": text})
        if response.status_code == 200:
            return response.json()["embedding"]
        else:
            raise RuntimeError(f"Ollama embedding request failed ({response.status_code}): {response.text}")

async def auto_populate_embedding(collection: str, doc: Dict[str, Any]) -> None:
    """Pre-computes embedding using Ollama if the provider is ollama and embedding is missing."""
    if TYPESENSE_EMBEDDING_PROVIDER != "ollama":
        return
    if "embedding" in doc and doc["embedding"] is not None:
        return
        
    text_to_embed = None
    if collection in ("session_ego", "session_working_memory"):
        text_to_embed = doc.get("semantic_text")
        if not text_to_embed:
            # Fallback auto-generation logic
            sub = doc.get("subject", "")
            pred = doc.get("predicate", "")
            obj = doc.get("object", "")
            if sub and pred and obj:
                text_to_embed = f"{sub} {pred} {obj}"
                doc["semantic_text"] = text_to_embed
    elif collection == "session_short_term_memory":
        text_to_embed = doc.get("content")
        
    if text_to_embed:
        try:
            doc["embedding"] = await get_ollama_embedding(text_to_embed)
        except Exception as exc:
            logger.warning(f"Failed to generate embedding for doc {doc.get('id')} in {collection}: {exc}")

async def init_typesense_collections() -> None:
    """Initialize all session storage collections in Typesense."""
    try:
        await ensure_ollama_model_pulled()
    except Exception as e:
        logger.warning(f"Ollama pre-start pull checks skipped/failed: {e}")
        
    logger.info("Initializing Typesense collections...")
    
    schemas = [
        {
            "name": "session_ego",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "session_id", "type": "string", "facet": True},
                {"name": "subject", "type": "string", "facet": True},
                {"name": "predicate", "type": "string", "facet": True},
                {"name": "object", "type": "string", "facet": True},
                {"name": "context", "type": "string", "facet": True, "optional": True},
                {"name": "semantic_text", "type": "string"},
                {"name": "timestamp", "type": "int64"},
                get_embedding_field_definition()
            ],
            "default_sorting_field": "timestamp"
        },
        {
            "name": "session_working_memory",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "session_id", "type": "string", "facet": True},
                {"name": "subject", "type": "string", "facet": True},
                {"name": "predicate", "type": "string", "facet": True},
                {"name": "object", "type": "string", "facet": True},
                {"name": "context", "type": "string", "facet": True, "optional": True},
                {"name": "semantic_text", "type": "string"},
                {"name": "timestamp", "type": "int64"},
                get_embedding_field_definition()
            ],
            "default_sorting_field": "timestamp"
        },
        {
            "name": "session_short_term_memory",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "session_id", "type": "string", "facet": True},
                {"name": "key", "type": "string", "facet": True, "optional": True},
                {"name": "content", "type": "string"},
                {"name": "role", "type": "string", "facet": True, "optional": True},
                {"name": "timestamp", "type": "int64"},
                get_embedding_field_definition()
            ],
            "default_sorting_field": "timestamp"
        }
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for schema in schemas:
            await check_and_create_collection(client, schema)

# --- CRUD Helper Operations ---

async def index_document(collection: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    """Index/Insert a single document into a Typesense collection."""
    await auto_populate_embedding(collection, doc)
    url = f"{TYPESENSE_URL}/collections/{collection}/documents"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, headers=HEADERS, json=doc)
        if response.status_code in (200, 201):
            return response.json()
        else:
            raise httpx.HTTPStatusError(
                f"Failed to index document in {collection}: {response.text}",
                request=response.request,
                response=response
            )

async def bulk_index_documents(collection: str, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Bulk index documents using Typesense import endpoint."""
    for doc in docs:
        await auto_populate_embedding(collection, doc)
        
    url = f"{TYPESENSE_URL}/collections/{collection}/documents/import?action=upsert"
    jsonl_data = "\n".join(json.dumps(doc) for doc in docs)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {**HEADERS, "Content-Type": "text/plain"}
        response = await client.post(url, headers=headers, content=jsonl_data)
        
        if response.status_code == 200:
            lines = response.text.strip().split("\n")
            results = []
            for line in lines:
                if line:
                    results.append(json.loads(line))
            return results
        else:
            raise httpx.HTTPStatusError(
                f"Failed bulk import to {collection}: {response.text}",
                request=response.request,
                response=response
            )

async def get_document(collection: str, doc_id: str) -> Dict[str, Any]:
    """Retrieve a document by ID."""
    url = f"{TYPESENSE_URL}/collections/{collection}/documents/{doc_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=HEADERS)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            raise KeyError(f"Document {doc_id} not found in {collection}")
        else:
            raise httpx.HTTPStatusError(
                f"Failed to retrieve document from {collection}: {response.text}",
                request=response.request,
                response=response
            )

async def delete_document(collection: str, doc_id: str) -> Dict[str, Any]:
    """Delete a single document by ID."""
    url = f"{TYPESENSE_URL}/collections/{collection}/documents/{doc_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.delete(url, headers=HEADERS)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            raise KeyError(f"Document {doc_id} not found in {collection}")
        else:
            raise httpx.HTTPStatusError(
                f"Failed to delete document from {collection}: {response.text}",
                request=response.request,
                response=response
            )

async def delete_documents_by_query(collection: str, filter_by: str) -> Dict[str, Any]:
    """Delete multiple documents matching a filter_by query."""
    url = f"{TYPESENSE_URL}/collections/{collection}/documents"
    params = {"filter_by": filter_by}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(url, headers=HEADERS, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            raise httpx.HTTPStatusError(
                f"Failed to bulk-delete from {collection} with filter '{filter_by}': {response.text}",
                request=response.request,
                response=response
            )

async def search_collection(collection: str, search_params: Dict[str, Any]) -> Dict[str, Any]:
    """Search documents in a collection."""
    # Auto-generate vector query if q is present, provider is ollama, and vector_query is not set yet
    if TYPESENSE_EMBEDDING_PROVIDER == "ollama" and "vector_query" not in search_params:
        q = search_params.get("q", "")
        if q and q != "*":
            try:
                emb = await get_ollama_embedding(q)
                limit = search_params.get("per_page", 10)
                search_params["vector_query"] = f"embedding:([{','.join(map(str, emb))}], k:{limit})"
            except Exception as exc:
                logger.warning(f"Failed to generate query embedding for '{q}': {exc}")
                
    url = f"{TYPESENSE_URL}/collections/{collection}/documents/search"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=HEADERS, params=search_params)
        if response.status_code == 200:
            return response.json()
        else:
            raise httpx.HTTPStatusError(
                f"Failed search in {collection}: {response.text}",
                request=response.request,
                response=response
            )
