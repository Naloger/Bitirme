from langgraph.graph import END, START, StateGraph

from services.Agentic.HelperAgents.QuadRDFAgent.QuadAgentNodes import extract_quads_node
from services.Agentic.HelperAgents.QuadRDFAgent.QuadAgentStates import QuadAgentState


def build_quad_graph():
    """
    Constructs the LangGraph for the QuadRDFAgent.
    Currently it is a very simple linear flow: START -> Extract -> END
    """
    builder = StateGraph(QuadAgentState)

    # Add nodes
    builder.add_node("extractor", extract_quads_node)

    # Define edges
    builder.add_edge(START, "extractor")
    builder.add_edge("extractor", END)

    return builder.compile()
