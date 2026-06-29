import io
import os
import sys

# Ensure project root is in sys.path before importing local services
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentStates import (
    LoopState,
)
from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopGraphBuilder import (
    build_loop_subgraph,
)
from services.Config import config


def initial_state(should_stop: bool = False) -> LoopState:
    """Return a fresh LoopState. Pass should_stop=True to skip the loop."""
    return LoopState(data=None, iteration=0, should_stop=should_stop)


if __name__ == "__main__":
    # Force UTF-8 stdout so Unicode doesn't crash on Windows
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )

    graph = build_loop_subgraph()

    print(f"Running demo ({config.MAX_LOOPS} full cycles then stop)...\n")
    demo_result = graph.invoke(initial_state())
    print("\nFinal state:", demo_result)
