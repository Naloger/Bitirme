from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from services.Agentic.MainAgents.SalienceMode.SalienceModels import SalienceState
from services.Agentic.MainAgents.SalienceMode.SalienceNodes import (
    run_default_subgraph,
    run_executive_subgraph,
    run_intent_analysis_node,
    salience_router_node,
)


def _route_subgraph(state: SalienceState) -> str:
    """Routes to the chosen subgraph node based on salience observation."""
    if state.target_subgraph == "DefaultMode":
        return "DefaultMode"
    return "ExecutiveControlMode"


def build_salience_graph() -> CompiledStateGraph:
    """Builds and compiles the Salience Mode Router graph."""
    builder = StateGraph(SalienceState)

    builder.add_node("IntentAnalysis", run_intent_analysis_node)
    builder.add_node("SalienceRouter", salience_router_node)
    builder.add_node("ExecutiveControlMode", run_executive_subgraph)
    builder.add_node("DefaultMode", run_default_subgraph)

    builder.add_edge(START, "IntentAnalysis")
    builder.add_edge("IntentAnalysis", "SalienceRouter")
    builder.add_edge("ExecutiveControlMode", END)
    builder.add_edge("DefaultMode", END)

    builder.add_conditional_edges(
        "SalienceRouter",
        _route_subgraph,
        {
            "ExecutiveControlMode": "ExecutiveControlMode",
            "DefaultMode": "DefaultMode",
        },
    )

    return builder.compile()

