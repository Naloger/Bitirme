from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlModels import (
    ECNState,
)
from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlNodes import (
    task_context_builder,
    task_evaluator,
    task_executor,
    task_finalizer,
    task_memory_manager,
    task_reasoner,
)

# ---------------------------------------------------------------------------
# Conditional Edge Routers
# ---------------------------------------------------------------------------


def _route_from_reasoner(state: ECNState) -> str:
    """Routes based on reasoner decision."""
    if state.reasoner_routing == "task_completed":
        return "task_completed"
    return "requires_tool_execution"


def _route_from_evaluator(state: ECNState) -> str:
    """Routes based on evaluator verdict."""
    if state.evaluation_status == "task_failed":
        return "task_failed"
    # Both step_success and step_error go through memory first
    return "continue"


# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------


def build_ecn_graph() -> CompiledStateGraph:
    """Build and compile the Executive Control Network (ECN) graph."""
    builder = StateGraph(ECNState)

    builder.add_node("TaskContextBuilder", task_context_builder)
    builder.add_node("TaskReasoner", task_reasoner)
    builder.add_node("TaskExecutor", task_executor)
    builder.add_node("TaskEvaluator", task_evaluator)
    builder.add_node("TaskMemoryManager", task_memory_manager)
    builder.add_node("TaskFinalizer", task_finalizer)

    builder.add_edge(START, "TaskContextBuilder")
    builder.add_edge("TaskContextBuilder", "TaskReasoner")
    builder.add_edge("TaskExecutor", "TaskEvaluator")
    builder.add_edge("TaskFinalizer", END)
    builder.add_edge("TaskMemoryManager", "TaskContextBuilder")

    builder.add_conditional_edges(
        "TaskReasoner",
        _route_from_reasoner,
        {"requires_tool_execution": "TaskExecutor", "task_completed": "TaskFinalizer"},
    )
    builder.add_conditional_edges(
        "TaskEvaluator",
        _route_from_evaluator,
        {
            "continue": "TaskMemoryManager",
            "task_failed": "TaskFinalizer",
        },
    )

    return builder.compile()
