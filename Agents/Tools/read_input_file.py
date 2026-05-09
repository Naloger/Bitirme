from __future__ import annotations

from pathlib import Path
from langchain_core.tools import tool

# Define the input file path for the intent parser node
BASE = Path(__file__).parent.parent / "Nodes" / "node_intent_parser"
INPUT_FILE = BASE / "Input.txt"

#TODO : FIX
# buna gerek yok , node kısmında değiştir

@tool
def read_input_file() -> str:
    """Reads the input text file and returns its content. Call this first to get context."""
    if not INPUT_FILE.exists():
        return f"Error: Input file not found at {INPUT_FILE}"
    return INPUT_FILE.read_text(encoding="utf-8").strip()
