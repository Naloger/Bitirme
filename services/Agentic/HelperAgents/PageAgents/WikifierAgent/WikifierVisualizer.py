import os
import sys

from services.Agentic.HelperAgents.PageAgents.WikifierAgent.WikifierGraphBuilder import (
    build_wikifier_graph,
)
from services.Agentic.MainAgents.visualize_graph import visualize

# Ensure project root is in sys.path before importing local services
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)


if __name__ == "__main__":
    print("Visualizing WikifierAgent...")
    visualize(build_wikifier_graph(), name="wikifier_graph", out_dir=_here)
