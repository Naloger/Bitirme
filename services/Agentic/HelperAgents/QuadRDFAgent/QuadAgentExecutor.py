import os
import sys

# Ensure project root is in sys.path before importing local services
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from services.Agentic.HelperAgents.QuadRDFAgent.QuadAgentModels import QuadAgentState
from services.Agentic.HelperAgents.QuadRDFAgent.QuadGraphBuilder import build_quad_graph

if __name__ == "__main__":
    sample_text = (
        "Sol is the personification of the Sun and a god in ancient Roman religion. It was long thought that Rome actually had two different, consecutive sun gods: "
        "The first, Sol Indiges (Latin: the deified sun), was thought to have been unimportant, "
        "disappearing altogether at an early period. Only in the late Roman Empire, "
        "scholars argued, did the solar cult re-appear with the arrival in Rome of "
        "the Syrian Sol Invictus (Latin: the unconquered sun), perhaps under the "
        "influence of the Mithraic myteries.[1] Publications from the mid-1990s "
        "have challenged the notion of two different sun gods in Rome, "
        "pointing to the abundant evidence for the continuity of the cult of "
        "Sol, and the lack of any clear differentiation – "
        "either in name or depiction – between the \"early\" and \"late\" "
        "Roman sun god.[2][3][4][5]"
        "Microsoft was founded by Bill Gates and Paul Allen. "
        "The company is headquartered in Redmond, Washington."
    )

    initial_state = QuadAgentState(
        input_text=sample_text,
        graph_id="doc_sample_0",
        extracted_quads=[],
        error=None,
    )

    graph = build_quad_graph()
    print("Executing QuadRDFAgent LangGraph...")
    result = graph.invoke(initial_state)

    print("\n--- Execution Finished ---")
    if result.get("error"):
        print(f"Error occurred: {result['error']}")
    else:
        for q in result.get("extracted_quads", []):
            print(
                f"({q.subject}) --[{q.predicate}]--> ({q.object})  | Graph: {q.graph}"
            )
