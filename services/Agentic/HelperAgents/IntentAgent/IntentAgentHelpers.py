from services.Agentic.HelperAgents.IntentAgent.IntentAgentModels import (
    IntentAgentState,
    IntentResult,
)


def analyze(x: str, k: str = "") -> IntentResult:
    """Invokes the compiled IntentAgent LangGraph to perform parsing."""
    from services.Agentic.HelperAgents.IntentAgent.IntentGraphBuilder import (
        build_intent_graph,
    )
    # IntentAgentState is a Pydantic model
    initial_state = IntentAgentState(
        message_text=x,
        context_info=k,
        analysis_result=None,
        error=None
    )

    graph = build_intent_graph()
    result = graph.invoke(initial_state)

    if result.get("error"):
        raise ValueError(f"Intent analysis graph failed: {result.get('error')}")

    res = result.get("analysis_result")
    assert res is not None
    return res
