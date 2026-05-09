from __future__ import annotations

from typing import Optional

from Agents.Nodes.node_stream_guard.Classes.StreamGuardMiddleware import StreamGuardMiddleware
from Agents.Nodes.node_stream_guard.Classes.StreamGuardConfig import StreamGuardConfig


def create_stream_guard_middleware(
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    max_loops: Optional[int] = None,
    **config_kwargs,
) -> StreamGuardMiddleware:
    """
    Factory function to create a StreamGuardMiddleware instance.

    Args:
        model: Ollama model name to use.
        base_url: Ollama API base URL.
        max_loops: Maximum retry attempts on loop detection.
        **config_kwargs: Additional StreamGuardConfig parameters.

    Returns:
        Configured StreamGuardMiddleware instance.
    """
    config_params = {}
    if model is not None:
        config_params["model"] = model
    if base_url is not None:
        config_params["base_url"] = base_url
    if max_loops is not None:
        config_params["max_loops"] = max_loops
    config_params.update(config_kwargs)
    return StreamGuardMiddleware(config=StreamGuardConfig(**config_params))
