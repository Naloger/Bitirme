from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentModels import (
    LoopState,
)


def node1(state: LoopState) -> LoopState:
    """Acquire / refresh data for this cycle."""
    return state  # placeholder implementation


def node2(state: LoopState) -> LoopState:
    """Transform / enrich the data produced by Node1."""

    return state  # placeholder implementation


def node3(state: LoopState) -> LoopState:
    """Evaluate / analyze the transformed data."""

    return state  # placeholder implementation


def node4(state: LoopState) -> LoopState:
    """
    Finalize the cycle result and increment the iteration counter.
    This node is the loop controller.
    """
    return state  # placeholder implementation


def _loop_or_exit(state: LoopState) -> str:
    """
    Called after Node4.
    Returns 'loop' to go back to Node1, or 'exit' to END.
    """
    return "exit" if state.should_stop else "loop"
