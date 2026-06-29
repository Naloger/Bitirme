from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentModels import (
    GraphState,
)
from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentPrompts import (
    CollectorNodePromptInner,
    CollectorNodePromptOuter,
    OrganizerNodePromptInner,
    OrganizerNodePromptOuter,
    ReflectorNodePromptInner,
    ReflectorNodePromptOuter,
    IntegratorNodePromptInner,
    IntegratorNodePromptOuter,
)

# Global configuration variable for the active prompt channel
channel = "inner_channel"


def collector_node(state: GraphState) -> GraphState:
    prompt = CollectorNodePromptInner if channel == "inner_channel" else CollectorNodePromptOuter
    print(f"  [collector_node] socketed prompt: {prompt}")
    return state


def organizer_node(state: GraphState) -> GraphState:
    prompt = OrganizerNodePromptInner if channel == "inner_channel" else OrganizerNodePromptOuter
    print(f"  [organizer_node] socketed prompt: {prompt}")
    return state


def reflector_node(state: GraphState) -> GraphState:
    prompt = ReflectorNodePromptInner if channel == "inner_channel" else ReflectorNodePromptOuter
    print(f"  [reflector_node] socketed prompt: {prompt}")
    return state


def integrator_node(state: GraphState) -> GraphState:
    """
    Finalize the cycle result and increment the iteration counter.
    This node is the loop controller.
    """
    prompt = IntegratorNodePromptInner if channel == "inner_channel" else IntegratorNodePromptOuter
    print(f"  [integrator_node] socketed prompt: {prompt}")
    return state

def _loop_or_exit(state: GraphState) -> str:
    """
    Called after Node4.
    Returns 'loop' to go back to Node1, or 'exit' to END.
    """
    return "exit" if state.should_stop else "loop"
