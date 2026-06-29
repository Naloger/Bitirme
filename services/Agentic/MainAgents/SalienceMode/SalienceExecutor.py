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
    """Invokes the Salience Router graph with the given user input."""
    graph = build_salience_graph()
    initial_state = SalienceState(user_input=user_input)
    return graph.invoke(initial_state)


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
    print("Salience Network Router Demo")
    print("=============================================================")

    # Demo 1: Executive Control Mode Task (requires tool/reasoning)
    exec_task = "Show me the current system datetime."
    print(f"\n--- Testing ECN Task: '{exec_task}' ---")
    exec_result = execute_salience_router(exec_task)
    print("\n--- ECN Run Result Summary ---")
    print(f"Target Subgraph: {exec_result.target_subgraph}")
    print(f"Explanation: {exec_result.explanation}")
    print(f"Result: {exec_result.result}")

    # Demo 2: Default Mode Task (repetition/simple data loop)
    default_task = "Execute a simple loop cycle data transformation on the value 'Hello World'."
    print(f"\n\n--- Testing DMN Task: '{default_task}' ---")
    default_result = execute_salience_router(default_task)
    print("\n--- DMN Run Result Summary ---")
    print(f"Target Subgraph: {default_result.target_subgraph}")
    print(f"Explanation: {default_result.explanation}")
    print(f"Result: {default_result.result}")
    print("=============================================================")
