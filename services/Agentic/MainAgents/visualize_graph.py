"""
General-purpose LangGraph visualizer using Mermaid.
"""

import importlib
import os
import sys

# Ensure project root is in sys.path before importing local services
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)


def visualize(
    compiled_graph,
    name: str = "graph",
    out_dir: str | None = None,
) -> None:
    """
    Visualize any compiled LangGraph graph using Mermaid PNG generation.

    Parameters
    ----------
    compiled_graph
        A compiled StateGraph (from `builder.compile()`).
    name
        Base name used for output filenames (no extension).
    out_dir
        Directory to save files in. Defaults to the directory of this script.
    """
    if out_dir is None:
        out_dir = os.path.dirname(os.path.abspath(__file__))

    out_path = os.path.join(out_dir, f"{name}.png")
    title = name.replace("_", " ").title()

    print(f"\nVisualizing graph: '{title}'")
    print("=" * 60)

    try:
        png_bytes = compiled_graph.get_graph().draw_mermaid_png()
        with open(out_path, "wb") as fh:
            fh.write(png_bytes)
        print(f"[Mermaid] saved -> {out_path}")
    except Exception as exc:
        print(f"[Mermaid] generation failed: {exc}")
        print(
            "Ensure you have network access or the correct backend for mermaid graph generation."
        )


def _cli_main() -> None:
    """
    CLI usage: python visualize_graph.py <module:function> [name]
    """
    if len(sys.argv) < 2:
        print(
            "Usage: python visualize_graph.py <module.path:builder_function> [graph_name]"
        )
        sys.exit(1)

    ref = sys.argv[1]
    graph_name = sys.argv[2] if len(sys.argv) > 2 else "graph"

    if ":" not in ref:
        print(f"ERROR: expected 'module:function', got '{ref}'")
        sys.exit(1)

    module_path, fn_name = ref.rsplit(":", 1)

    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        print(f"ERROR: cannot import module '{module_path}': {exc}")
        sys.exit(1)

    builder_fn = getattr(module, fn_name, None)
    if builder_fn is None:
        print(f"ERROR: '{fn_name}' not found in '{module_path}'")
        sys.exit(1)

    compiled = builder_fn()
    visualize(compiled, name=graph_name, out_dir=os.getcwd())


if __name__ == "__main__":
    _cli_main()
