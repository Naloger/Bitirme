from langgraph.graph import END, START, StateGraph

from services.Agentic.HelperAgents.QuadRDFAgent.QuadAgentModels import QuadAgentState
from services.Agentic.HelperAgents.QuadRDFAgent.QuadAgentNodes import extract_quads_node


def build_quad_graph():
    """
    Constructs the LangGraph for the QuadRDFAgent.
    Currently it is a very simple linear flow: START -> Extract -> END
    """
    builder = StateGraph(QuadAgentState)

    # Add nodes
    builder.add_node("extract_quads_node", extract_quads_node)

    # Define edges
    builder.add_edge(START, "extract_quads_node")
    builder.add_edge("extract_quads_node", END)

    return builder.compile()
