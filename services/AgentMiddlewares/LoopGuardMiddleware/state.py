from __future__ import annotations
from typing import Optional
from langchain.agents import AgentState
from typing_extensions import NotRequired


# Avoid hard dependency on LangChain for the state base class. If
# langchain.agents.middleware.AgentState is available, use it; otherwise
# provide a minimal stand-in so type-based code still works.
class StreamGuardState(AgentState):
    """Extended agent state for stream guard tracking.

    This class mirrors the previous definition in `node_LoopGuard.py` but is
    placed in a small shared module to avoid circular imports between the
    runtime node script and the middleware implementation.
    """

    stream_guard_output: NotRequired[Optional[str]]
    stream_guard_thinking: NotRequired[Optional[str]]
    stream_guard_loop_restarts: NotRequired[Optional[int]]
    stream_guard_model: NotRequired[Optional[str]]
    stream_guard_success: NotRequired[Optional[bool]]

