from __future__ import annotations

from typing import Optional

from services.Agentic.AgentMiddlewares.LoopGuardMiddleware.Classes.StreamGuardMiddleware import (
    StreamGuardMiddleware,
)


def create_stream_guard_middleware(
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    max_loops: Optional[int] = None,
    **kwargs,
) -> StreamGuardMiddleware:
    """Create StreamGuardMiddleware using the loaded config with optional overrides."""
    overrides = {}
    if model is not None:
        overrides["model"] = model
    if base_url is not None:
        overrides["base_url"] = base_url
    if max_loops is not None:
        overrides["max_loops"] = max_loops
    overrides.update(kwargs)

    return StreamGuardMiddleware(**overrides)
