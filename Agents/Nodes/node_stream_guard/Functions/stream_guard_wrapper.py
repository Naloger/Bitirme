from typing import Callable
from langchain.agents.middleware import (
    wrap_model_call,
    ModelRequest,
    ModelResponse,
    ExtendedModelResponse,
)
from Agents.Nodes.node_stream_guard.Classes.StreamGuardMiddleware import StreamGuardMiddleware


@wrap_model_call
def stream_guard_wrapper(
    cfg,
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ExtendedModelResponse:
    # Instantiate middleware internally to reuse logic
    mware = StreamGuardMiddleware(config=cfg)
    return mware.wrap_model_call(request, handler)
