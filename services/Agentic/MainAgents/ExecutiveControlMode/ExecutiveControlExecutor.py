import os
import sys

# Reconfigure stdout/stderr to use UTF-8 to prevent cp1254 UnicodeEncodeErrors on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlGraphBuilder import (
    build_ecn_graph,
)
from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlHelpers import (
    default_initial_state,
)

# Ensure project root is in sys.path before importing local services
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)


def execute_task(task_id: str, task_desc: str) -> dict:
    """Executes the ECN agent on a given task description."""
    ecn = build_ecn_graph()
    initial_state = default_initial_state(task_id, task_desc)
    result = ecn.invoke(initial_state)
    return result

if __name__ == "__main__":
    task_id = "task_demo_elden_5"
    task_desc = "Tell me about most important elden ring characters."

    graph = build_ecn_graph()

    print("Executing ECN Agent LangGraph...")
    initial_state = default_initial_state(task_id, task_desc)
    result = graph.invoke(initial_state)

    print("\n--- Execution Finished ---")
    print(f"  Task ID:    {result['task_id']}")
    print(f"  Task:       {result['task']}")
    print(f"  Iterations: {result['iteration']}")
    print(f"  Routing:    {result['reasoner_routing']}")
    print(f"  Memory:     {result['memory']}")
    print(f"  Reasoner Output:\n{result['reasoning']}")

