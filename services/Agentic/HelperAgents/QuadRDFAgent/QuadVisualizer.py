import os
import sys

# Ensure project root is in sys.path before importing local services
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from services.Agentic.HelperAgents.QuadRDFAgent.QuadGraphBuilder import build_quad_graph
from services.Agentic.MainAgents.visualize_graph import visualize


if __name__ == "__main__":
    visualize(build_quad_graph(), name="quad_graph", out_dir=_here)
