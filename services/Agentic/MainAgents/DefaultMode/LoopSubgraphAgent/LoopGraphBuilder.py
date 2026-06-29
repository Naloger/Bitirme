from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentModels import (
    LoopState,
)
from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentNodes import (
    _loop_or_exit,
    node1,
    node2,
    node3,
    node4,
)


def build_loop_subgraph() -> CompiledStateGraph[Any, Any, Any, Any]:
    """
    Build and compile the 4-node looping subgraph.
    Cycle: Node1 -> Node2 -> Node3 -> Node4 -> Node1 (-> ... -> END)
    """
    builder = StateGraph(LoopState)

    builder.add_node("Node1", node1)
    builder.add_node("Node2", node2)
    builder.add_node("Node3", node3)
    builder.add_node("Node4", node4)

    builder.add_edge(START, "Node1")
    builder.add_edge("Node1", "Node2")
    builder.add_edge("Node2", "Node3")
    builder.add_edge("Node3", "Node4")

    # Node4 is the loop gate
    builder.add_conditional_edges(
        "Node4",
        _loop_or_exit,
        {
            "loop": "Node1",  # <- back to the top
            "exit": END,  # <- clean exit
        },
    )

    return builder.compile()
