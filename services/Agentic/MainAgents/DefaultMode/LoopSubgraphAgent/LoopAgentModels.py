from typing import Any, Dict, List

from pydantic import BaseModel, Field


class GraphState(BaseModel):
    """Central state object passed between every node."""
    rdf_graph_memory_recall: Dict[Any, Any] = Field(default_factory=dict)
    raw_internal: List[Dict[str, Any]] = Field(default_factory=list)
    raw_external: List[Dict[str, Any]] = Field(default_factory=list)

