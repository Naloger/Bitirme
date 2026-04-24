"""
LangGraph Node Template

Basic structure for creating a LangGraph node:
1. Define state schema using TypedDict
2. Create node function that processes state
3. Return updated state dict (only changed fields needed)

Graph usage example (in comment):
    from langgraph.graph import StateGraph, START, END

    graph_builder = StateGraph(MyState)
    graph_builder.add_node("my_node", my_node_function)
    graph_builder.add_edge(START, "my_node")
    graph_builder.add_edge("my_node", END)
    graph = graph_builder.compile()

    result = graph.invoke({"field1": "value1"})
"""

from typing import Any, cast
from typing_extensions import TypedDict

# ============================================================================
# State Definition
# ============================================================================


class MyState(TypedDict, total=False):
    """
    State schema for the node.

    Attributes:
        input_field (str): Primary input field
        output_field (str): Primary output field
        error (str): Error message if any
    """

    input_field: str
    output_field: str
    error: str


# ============================================================================
# Node Function
# ============================================================================


def my_node(state: MyState) -> MyState:
    """
    Main node processing function.

    Args:
        state: Current state containing input fields

    Returns:
        Updated state dict with processed output
    """
    try:
        # Extract input
        input_data = state.get("input_field", "")

        if not input_data:
            return {"output_field": "", "error": "Empty input"}

        # Process logic here
        result = input_data.upper()  # Example: simple transformation

        return {"output_field": result, "error": ""}

    except Exception as exc:
        return {"output_field": "", "error": f"Processing failed: {exc}"}


# ============================================================================
# Optional: Helper Functions
# ============================================================================


def preprocess(data: str) -> str:
    """Preprocessing step."""
    return data.strip()


def postprocess(data: str) -> str:
    """Postprocessing step."""
    return data.lower()


# ============================================================================
# Optional: Build and Test Graph (for standalone testing)
# ============================================================================

if __name__ == "__main__":
    # Uncomment to test the node
    from langgraph.graph import StateGraph, START, END

    # Build graph
    graph_builder = StateGraph(cast(Any, MyState))
    graph_builder.add_node("process", cast(Any, my_node))
    graph_builder.add_edge(START, "process")
    graph_builder.add_edge("process", END)
    graph = graph_builder.compile()

    # Test
    test_input = {"input_field": "hello world"}
    output = graph.invoke(test_input)
    print(f"Input: {test_input}")
    print(f"Output: {output}")
