from __future__ import annotations

from typing import Optional

from Agents.Nodes.node_stream_guard.Classes.StreamGuardConfig import StreamGuardConfig
from Agents.Nodes.node_stream_guard.Functions.stream_guard_wrapper import stream_guard_wrapper


def create_stream_guard_decorator(
    config: Optional[StreamGuardConfig] = None,
    **kwargs,
):
    """
    Factory for decorator-based stream guard middleware.

    Use for simple, single-hook scenarios. For complex configuration,
    prefer the class-based StreamGuardMiddleware.
    """
    config or StreamGuardConfig(**kwargs)

    return stream_guard_wrapper
