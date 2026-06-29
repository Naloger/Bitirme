from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentModels import (
    GraphState,
)
from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentNodes import (
    _loop_or_exit,
    collector_node,
    integrator_node,
    organizer_node,
    reflector_node,
)


def build_loop_subgraph() -> CompiledStateGraph[Any, Any, Any, Any]:
    """
    Build and compile the 4-node looping subgraph.
    Cycle: Node1 -> Node2 -> Node3 -> Node4 -> Node1 (-> ... -> END)
    """
    builder = StateGraph(GraphState)

    builder.add_node("collector", collector_node)
    builder.add_node("organizer", organizer_node)
    builder.add_node("reflector", reflector_node)
    builder.add_node("integrator", integrator_node)


    builder.add_edge(START, "collector")
    builder.add_edge("collector", "organizer")
    builder.add_edge("organizer", "reflector")
    builder.add_edge("reflector", "integrator")

    # Node4 is the loop gate
    builder.add_conditional_edges(
        "integrator",
        _loop_or_exit,
        {
            "loop": "collector",  # <- back to the top
            "exit": END,  # <- clean exit
        },
    )

    return builder.compile()
