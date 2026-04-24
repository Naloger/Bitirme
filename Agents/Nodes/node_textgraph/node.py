"""Word-graph LangGraph node.

Pipeline:
    tokenize_node  ->  build_graph_node  ->  format_node

- Reads Input.txt, tokenizes words
- Builds a minimal graph (nodes = unique words, edges = co-occurrence within window)
- Writes Output.txt
No LLM used — purely rule-based.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END


BASE = Path(__file__).parent
INPUT = BASE / "Input.txt"
OUTPUT = BASE / "Output.txt"


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class WordGraphState(BaseModel):
    """Shared state passed between nodes."""

    raw_text: str = ""
    tokens: List[str] = []
    nodes: Dict[str, int] = {}  # word -> id
    edges: Dict[str, int] = {}  # "word1|word2" -> weight  (JSON-safe key)
    output_text: str = ""
    error: str = ""
    window: int = 2


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def tokenize_node(state: WordGraphState) -> dict[str, Any]:
    """Split raw_text into lowercase word tokens."""
    if not state.raw_text:
        return {"error": "raw_text is empty.", "tokens": []}

    tokens = re.findall(r"\w+", state.raw_text, flags=re.UNICODE)
    tokens = [t.lower() for t in tokens if t.strip()]

    if not tokens:
        return {"error": "No tokens found in input.", "tokens": []}

    return {"tokens": tokens, "error": ""}


def build_graph_node(state: WordGraphState) -> dict[str, Any]:
    """Assign node IDs and compute co-occurrence edge weights."""
    if state.error:
        return {}

    tokens = state.tokens
    window = state.window

    nodes: Dict[str, int] = {}
    for t in tokens:
        if t not in nodes:
            nodes[t] = len(nodes)

    # Edges: all pairs within the sliding window; key is pipe-joined sorted pair
    # so it stays a plain string (Pydantic state requires JSON-serialisable keys).
    edges: Dict[str, int] = {}
    for i, t in enumerate(tokens):
        for j in range(i + 1, min(i + window + 1, len(tokens))):
            a, b = tokens[i], tokens[j]
            key = "|".join(sorted((a, b)))
            edges[key] = edges.get(key, 0) + 1

    return {"nodes": nodes, "edges": edges}


def format_node(state: WordGraphState) -> dict[str, Any]:
    """Render nodes and edges to a human-readable string."""
    if state.error:
        return {"output_text": f"ERROR: {state.error}"}

    lines: List[str] = [
        "# Nodes (word -> id)",
        *[
            f"{idx}: {word}"
            for word, idx in sorted(state.nodes.items(), key=lambda x: x[1])
        ],
        "",
        "# Edges (word1, word2) : weight",
    ]

    # Reconstruct pairs from pipe-joined keys for display.
    # Split into exactly two parts and unpack explicitly to satisfy Tuple[str, str].
    edge_items: List[Tuple[Tuple[str, str], int]] = []
    for k, v in state.edges.items():
        left, right = k.split("|", 1)
        edge_items.append(((left, right), v))

    for (a, b), w in sorted(edge_items, key=lambda x: (-x[1], x[0])):
        lines.append(f"{a} -- {b} : {w}")

    return {"output_text": "\n".join(lines)}


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------


def create_word_graph_pipeline() -> Any:
    """Build and compile the LangGraph pipeline."""
    graph = StateGraph(state_schema=WordGraphState)

    graph.add_node("tokenize", tokenize_node)
    graph.add_node("build_graph", build_graph_node)
    graph.add_node("format", format_node)

    graph.add_edge(START, "tokenize")
    graph.add_edge("tokenize", "build_graph")
    graph.add_edge("build_graph", "format")
    graph.add_edge("format", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not INPUT.exists():
        print(f"Input file not found: {INPUT}")
    else:
        raw = INPUT.read_text(encoding="utf-8")

        pipeline = create_word_graph_pipeline()
        raw_result = pipeline.invoke(WordGraphState(raw_text=raw, window=2))
        result = WordGraphState.model_validate(raw_result)

        if result.error:
            print(f"Pipeline error: {result.error}")
        else:
            OUTPUT.write_text(result.output_text, encoding="utf-8")
            print(f"Graph node processed: {INPUT} -> {OUTPUT}")
