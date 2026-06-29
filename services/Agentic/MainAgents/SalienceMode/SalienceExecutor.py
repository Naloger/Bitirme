import io
import os
import sys

# Ensure project root is in sys.path before importing local services
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from services.Agentic.MainAgents.SalienceMode.SalienceGraphBuilder import (
    build_salience_graph,
)
from services.Agentic.MainAgents.SalienceMode.SalienceModels import SalienceState


def execute_salience_router(user_input: str) -> SalienceState:
    """Streams the Salience Router graph execution and returns the final state."""
    graph = build_salience_graph()
    initial_state = SalienceState(user_input=user_input)
    
    state_data = initial_state.model_dump()
    print(f"\n>>> Starting streaming graph execution for: '{user_input}'")
    
    for event in graph.stream(initial_state, stream_mode="updates"):
        for node_name, node_update in event.items():
            print(f"\n  [Stream] Node '{node_name}' finished. State updates:")
            for key, val in node_update.items():
                if val:
                    # Format output to be clean and human-readable
                    if isinstance(val, dict):
                        print(f"    • {key}: dict with keys {list(val.keys())}")
                    elif isinstance(val, list):
                        print(f"    • {key}: list with {len(val)} items")
                    else:
                        truncated_val = str(val)[:200] + "..." if len(str(val)) > 200 else str(val)
                        print(f"    • {key}: {truncated_val}")
            # Accumulate state updates
            state_data.update(node_update)
            
    return SalienceState(**state_data)


if __name__ == "__main__":
    # Force UTF-8 stream output to prevent character encoding crashes in localized consoles (Turkish/cp1254)
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )

    print("=============================================================")
    print("Salience Network Router")
    print("=============================================================")

    # Default task or command line argument if provided
    task = "Execute a simple loop cycle data transformation on the value 'Hello World'."
    if len(sys.argv) > 1:
        task = sys.argv[1]

    print(f"\n[Network Executing] Task: '{task}'")
    result = execute_salience_router(task)

    print("\n=============================================================")
    print("FINAL SUMMARY")
    print("=============================================================")
    print(f"Target Subgraph: {result.target_subgraph}")
    print(f"Explanation: {result.explanation}")
    print(f"Result: {result.result}")
    print("=============================================================")
