from typing import List, Optional, TypedDict

from services.Agentic.HelperAgents.QuadRDFAgent.QuadAgentModels import Quad


class QuadAgentState(TypedDict):
    """The state dictionary for the LangGraph QuadRDFAgent."""

    input_text: str
    graph_id: str
    extracted_quads: List[Quad]
    error: Optional[str]
