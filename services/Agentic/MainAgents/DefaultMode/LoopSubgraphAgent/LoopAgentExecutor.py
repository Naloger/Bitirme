import io
import os
import sys

# Ensure project root is in sys.path before importing local services
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentGraphBuilder import (
    build_loop_subgraph,
)
from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentModels import (
    GraphState,
)


def main():
    # Force UTF-8 stdout so Unicode doesn't crash on Windows
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )

    graph = build_loop_subgraph()

    init_state = GraphState(
        raw_internal=[],
        raw_external=[],
        knowledge_graph={"nodes": [], "edges": [], "communities": [], "index": {}},
        validation_report={"issues": [], "inferred_edges": [], "confidence_map": {}, "anomalous_nodes": []},
        decision={"priority_nodes": [], "impact": {}, "actions": [], "working_graph": {}},
        iteration=0,
        should_stop=False,
    )

    print("=" * 60)
    print("  Cognitive Graph Operating System — starting")
    print("=" * 60)

    final_state = graph.invoke(init_state)

    print("\n" + "=" * 60)
    print("  FINAL DECISION SUMMARY")
    print("=" * 60)
    actions = final_state["decision"]["actions"]
    print(f"  Total iterations : {final_state['iteration']}")
    print(f"  Actions dispatched: {len(actions)}")
    for a in actions:
        print(f"    • [{a['type']}] target={a['target']} concept={a['concept']} "
              f"conf={a['confidence']:.2f} risk={a['risk_score']:.2f}")

    issues = final_state["validation_report"]["issues"]
    print(f"  Validation issues : {len(issues)}")
    inferred = final_state["validation_report"]["inferred_edges"]
    print(f"  Inferred edges    : {len(inferred)}")


if __name__ == "__main__":
    main()

