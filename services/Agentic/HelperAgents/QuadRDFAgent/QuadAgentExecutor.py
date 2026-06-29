import os
import sys

# Ensure project root is in sys.path before importing local services
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from services.Agentic.HelperAgents.QuadRDFAgent.QuadGraphBuilder import build_quad_graph


if __name__ == "__main__":
    sample_text = (
        "Microsoft was founded by Bill Gates and Paul Allen. "
        "The company is headquartered in Redmond, Washington."
    )

    initial_state = {
        "input_text": sample_text,
        "graph_id": "doc_microsoft_history",
        "extracted_quads": [],
        "error": None,
    }

    graph = build_quad_graph()

    print("Executing QuadRDFAgent LangGraph...")
    result = graph.invoke(initial_state)

    print("\n--- Execution Finished ---")
    if result["error"]:
        print(f"Error occurred: {result['error']}")
    else:
        for q in result["extracted_quads"]:
            print(
                f"({q.subject}) --[{q.predicate}]--> ({q.object})  | Graph: {q.graph}"
            )
