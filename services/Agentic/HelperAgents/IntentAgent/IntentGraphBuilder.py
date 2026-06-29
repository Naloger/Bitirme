from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from services.Agentic.HelperAgents.IntentAgent.IntentAgentModels import IntentAgentState
from services.Agentic.HelperAgents.IntentAgent.IntentAgentNodes import (
    analyze_intent_node,
)


def build_intent_graph() -> CompiledStateGraph[Any, Any, Any, Any]:
    """
    Builds the LangGraph for IntentAgent analysis.
    Flow: START -> analyze_intent -> END
    """
    builder = StateGraph(IntentAgentState)

    # Add Nodes
    builder.add_node("analyze_intent", analyze_intent_node)

    # Define flow
    builder.add_edge(START, "analyze_intent")
    builder.add_edge("analyze_intent", END)

    return builder.compile()
