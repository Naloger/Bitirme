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
    # Reconfigure stdout/stderr to use UTF-8 and enable line buffering to prevent cp1254 UnicodeEncodeErrors on Windows and ensure immediate output flush
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)

    # Read from stdin ONLY if explicitly instructed by passing --stdin flag,
    # otherwise default to the rich sample text input to avoid blocking process pipes.
    input_text = (
        "SystemEvent: CPU_SPIKE\n"
        "Time: 2026-06-29T18:30:00Z\n"
        "Details: Worker node worker_node_3 experienced CPU utilization of 94.5%.\n"
        "This high load triggered warning logs: 'High memory allocation detected on worker_node_3'.\n"
        "Additionally, the external sensor_endpoint api_node is down at url https://api.example.com/feed."
    )
    print("Using default Microsoft GraphRAG alike sample text input:")

    print("-" * 70)
    print(input_text.strip())
    print("-" * 70)

    graph = build_loop_subgraph()

    init_state = GraphState(
        input_text=input_text,
        raw_internal=[],
        raw_external=[],
        knowledge_graph=[],
        validation_report={"issues": [], "confidence_map": {}, "anomalous_nodes": []},
        decision={"priority_nodes": [], "impact": {}, "actions": [], "working_graph": {}},
        iteration=0,
        should_stop=False,
    )

    print("\n" + "=" * 60)
    print("  Cognitive Graph Operating System — starting RDF Quadstore parser")
    print("=" * 60)

    final_state = graph.invoke(init_state)

    print("\n" + "=" * 60)
    print("  FINAL DECISION SUMMARY")
    print("=" * 60)
    actions = final_state["decision"]["actions"]
    print(f"  Total iterations : {final_state['iteration']}")
    print(f"  Actions dispatched: {len(actions)}")
    for a in actions:
        print(f"    • [{a['type']}] target={a['target']} concept={a['concept']}")

    quads = final_state["knowledge_graph"]
    print(f"\n  Final Compiled Quadstore (Total {len(quads)} Atomic Quads):")
    for q in quads:
        print(f"    • Subject: {q.subject:<15} | Predicate: {q.predicate:<15} | Object: {q.object:<30} | Graph URI: {q.graph}")

    # Persist final compiled quadstore results to the database
    from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentTools import tool_write_to_quadstore
    print("\n  Writing final compiled quads to database...")
    tool_write_to_quadstore(quads, overwrite=True, clear_contexts=["llm_input"])

    issues = final_state["validation_report"].get("issues", [])
    print(f"\n  Validation issues : {len(issues)}")


if __name__ == "__main__":
    main()
