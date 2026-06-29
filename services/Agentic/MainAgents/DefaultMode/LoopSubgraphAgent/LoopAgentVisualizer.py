import os
import sys

from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentGraphBuilder import (
    build_loop_subgraph,
)
from services.Agentic.MainAgents.visualize_graph import visualize

# Ensure project root is in sys.path before importing local services
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

if __name__ == "__main__":
    print("Visualizing LoopSubgraphAgent...")
    visualize(build_loop_subgraph(), name="loop_subgraph", out_dir=_here)
