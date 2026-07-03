from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class RDFQuadBase(BaseModel):
    subject: str = Field(..., description="Subject of the RDF statement (e.g., node name, URI)")
    predicate: str = Field(..., description="Predicate of the RDF statement (e.g., relation name)")
    object: str = Field(..., description="Object of the RDF statement (e.g., node name, URI, literal value)")
    context: Optional[str] = Field(None, description="Context, graph, or domain of the RDF statement")
    semantic_text: Optional[str] = Field(None, description="Natural language sentence representing the quad. Automatically generated if not provided.")

class RDFQuadCreate(RDFQuadBase):
    id: Optional[str] = Field(None, description="Optional unique identifier. If not provided, a random UUID will be generated.")
    embedding: Optional[List[float]] = Field(None, description="Optional vector embedding for semantic search (1536 dimensions)")

class RDFQuadRead(RDFQuadBase):
    id: str = Field(..., description="Unique document ID in Typesense")
    session_id: str = Field(..., description="Session identifier")
    timestamp: int = Field(..., description="Unix timestamp of when the quad was recorded")

class ShortTermMemoryBase(BaseModel):
    key: Optional[str] = Field(None, description="Optional key to associate with this memory block")
    content: str = Field(..., description="The textual content or message stored in this memory block")
    role: Optional[str] = Field(None, description="Optional agent/user/system role associated with the memory")

class ShortTermMemoryCreate(ShortTermMemoryBase):
    id: Optional[str] = Field(None, description="Optional unique identifier. If not provided, a random UUID will be generated.")
    embedding: Optional[List[float]] = Field(None, description="Optional vector embedding for semantic search (1536 dimensions)")

class ShortTermMemoryRead(ShortTermMemoryBase):
    id: str = Field(..., description="Unique document ID in Typesense")
    session_id: str = Field(..., description="Session identifier")
    timestamp: int = Field(..., description="Unix timestamp of when the memory was recorded")

class SearchQuery(BaseModel):
    q: str = Field(default="*", description="Search query string. Use '*' for all documents.")
    query_by: Optional[str] = Field(None, description="Comma-separated fields to search. Defaults are collection-specific.")
    filter_by: Optional[str] = Field(None, description="Filter string using Typesense syntax (e.g. 'subject:=User1').")
    vector: Optional[List[float]] = Field(None, description="Optional vector for semantic/nearest-neighbor search.")
    limit: int = Field(default=20, ge=1, le=250, description="Max documents to return")
    offset: int = Field(default=0, ge=0, description="Pagination offset")

class SearchResultItem(BaseModel):
    document: Dict[str, Any] = Field(..., description="The raw retrieved document")
    highlight: Dict[str, Any] = Field(default_factory=dict, description="Field highlight snippets")
    text_match: Optional[int] = Field(None, description="Text match score")
    vector_distance: Optional[float] = Field(None, description="Vector search distance metric (if vector query used)")

class SearchResponse(BaseModel):
    found: int = Field(..., description="Total documents matching the query")
    took_ms: int = Field(..., description="Search execution time in milliseconds")
    hits: List[SearchResultItem] = Field(..., description="Matched items")
