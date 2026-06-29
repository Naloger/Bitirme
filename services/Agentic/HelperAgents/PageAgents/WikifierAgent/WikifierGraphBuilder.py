from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from services.Agentic.HelperAgents.PageAgents.WikifierAgent.WikifierAgentModels import (
    WikifierAgentState,
)
from services.Agentic.HelperAgents.PageAgents.WikifierAgent.WikifierAgentNodes import (
    categories_node,
    links_node,
    metadata_node,
    overview_node,
    sections_node,
)


def build_wikifier_graph() -> CompiledStateGraph[Any, Any, Any, Any]:
    """
    Builds the sequential LangGraph for page wikification.
    Flow: START -> overview -> sections -> categories -> links -> metadata -> END
    Short-circuits to END if an extraction error is encountered at any stage.
    """
    builder = StateGraph(WikifierAgentState)

    # Add Nodes
    builder.add_node("overview", overview_node)
    builder.add_node("sections", sections_node)
    builder.add_node("categories", categories_node)
    builder.add_node("links", links_node)
    builder.add_node("metadata", metadata_node)

    # Helper for short-circuiting on errors
    def route_after(next_node: str):
        return lambda state: END if state.error else next_node

    # Define flow
    builder.add_edge(START, "overview")
    builder.add_conditional_edges( "overview", route_after("sections"), {"sections": "sections", END: END})
    builder.add_conditional_edges( "sections", route_after("categories"), {"categories": "categories", END: END})
    builder.add_conditional_edges( "categories", route_after("links"), {"links": "links", END: END})
    builder.add_conditional_edges("links", route_after("metadata"), {"metadata": "metadata", END: END})
    builder.add_edge("metadata", END)

    return builder.compile()
