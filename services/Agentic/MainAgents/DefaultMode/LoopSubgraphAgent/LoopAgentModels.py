from typing import Any

from pydantic import BaseModel


class LoopState(BaseModel):
    """Shared state flowing through every node in the subgraph."""

    data: Any  # arbitrary payload; nodes can transform it freely
    iteration: int  # counts completed full cycles (Node1→2→3→4)
    should_stop: bool  # flip to True to exit — the ONLY exit condition
