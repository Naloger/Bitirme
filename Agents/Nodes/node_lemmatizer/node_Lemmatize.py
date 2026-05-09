from pathlib import Path
from typing import Any, cast

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from support_lib.Lemmatizer.lemmatize_text import lemmatize_text

BASE = Path(__file__).parent
INPUT = BASE / "Input.txt"
OUTPUT = BASE / "Output.txt"


class LemmatizerState(TypedDict, total=False):
    text: str
    lemmatized_lines: list[str]
    error: str


def lemmatize_node(state: LemmatizerState) -> LemmatizerState:
    """Process text through lemmatization pipeline."""
    input_text = state.get("text", "")
    if not input_text.strip():
        return {"lemmatized_lines": [], "error": "Empty input text."}

    lines = lemmatize_text(input_text)
    return {"lemmatized_lines": lines, "error": ""}


def build_lemmatizer_graph() -> Any:
    graph_builder = StateGraph(cast(Any, LemmatizerState))
    graph_builder.add_node("lemmatize", cast(Any, lemmatize_node))
    graph_builder.add_edge(START, "lemmatize")
    graph_builder.add_edge("lemmatize", END)
    return graph_builder.compile()


def process(text: str) -> list[str]:
    graph = build_lemmatizer_graph()
    result: dict[str, Any] = graph.invoke({"text": text})
    return list(result.get("lemmatized_lines", []))


def main() -> None:
    if not INPUT.exists():
        print(f"Input file not found: {INPUT}")
        return

    source_text = INPUT.read_text(encoding="utf-8")
    graph = build_lemmatizer_graph()
    result: dict[str, Any] = graph.invoke({"text": source_text})

    error = str(result.get("error", "")).strip()
    if error:
        print(f"[WARN] {error}")

    output_lines = result.get("lemmatized_lines", [])
    OUTPUT.write_text("\n".join(output_lines), encoding="utf-8")
    print(f"Lemmatizer processed: {INPUT} -> {OUTPUT}")


if __name__ == "__main__":
    main()
