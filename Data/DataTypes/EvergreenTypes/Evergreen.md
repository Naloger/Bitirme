# SYSTEM PROMPT: AI COPILOT / AGENT INSTRUCTIONS
# PROJECT: Version-Controlled Evergreen Zettelkasten (Local LLM System)

## 1. Project Overview
You are tasked with building a local, Python-based knowledge management system for an LLM agent. This system merges a Git-like version control mechanism (using delta-encoding) with a Zettelkasten knowledge graph. The goal is to allow the LLM to autonomously spawn, link, and evolve atomic notes over time, tracking its own conceptual maturation via commit history.

## 2. Tech Stack Requirements
- **Language:** Python 3.10+
- **Database:** SQLite3 (local file `zettelkasten.db`)
- **Data Validation:** `pydantic`
- **Diffing:** Built-in `difflib`
- **Agent Integration:** Standard Python functions typed for easy extraction into LLM tool-calling schemas (e.g., OpenAI function calling or LangChain `@tool`).

## 3. Database Schema & Data Models
Implement a local SQLite database that maps to these Pydantic models. 

### A. Zettel (The Note)
- `note_id`: string (UUID, Primary Key)
- `title`: string
- `status`: string (default: 'fleeting', options: 'fleeting', 'literature', 'evergreen')
- `head_commit_id`: string (Foreign Key to NoteCommit, nullable)

### B. NoteCommit (The Version History)
- `commit_id`: string (UUID, Primary Key)
- `note_id`: string (Foreign Key to Zettel)
- `parent_commit_id`: string (Foreign Key to NoteCommit, nullable)
- `timestamp`: datetime
- `message`: string (The LLM's reasoning for the change)
- `diff_patch`: string (Unified diff format string)

### C. Links (The Graph Edges)
- `source_id`: string (Foreign Key to Zettel)
- `target_id`: string (Foreign Key to Zettel)

## 4. Core Modules to Implement

### Module 1: `diff_engine.py`
Create a utility class to handle string comparisons.
- `create_patch(old_text: str, new_text: str) -> str`: Use `difflib.unified_diff`.
- `apply_patch(old_text: str, patch: str) -> str`: Reconstruct a file from its diffs. (Implement a basic line-by-line patch applier, or use `diff_match_patch` if external dependencies are allowed).

### Module 2: `db_manager.py`
Create a class to handle SQLite connections and queries.
- `initialize_db()`: Create tables if they don't exist.
- `get_note_content(note_id)`: Reconstructs the current text of a note by walking the commit history from the initial commit up to `head_commit_id`.
- `save_note()` & `save_commit()`
- `get_links(note_id)` & `add_link()`

### Module 3: `agent_tools.py`
Implement the following functions. Include detailed Google-style docstrings, as these will be parsed directly into LLM function schemas.

1. `spawn_note(title: str, content: str, links: list[str] = []) -> str`
   - Creates a new Zettel.
   - Creates an initial commit with the full content as the "diff" against an empty string.
   - Returns the new `note_id`.

2. `evolve_note(note_id: str, new_content: str, message: str) -> str`
   - Fetches current content via `db_manager`.
   - Generates a diff patch via `diff_engine`.
   - Saves a new `NoteCommit` to the DB.
   - Updates the Zettel's `head_commit_id`.
   - Returns the new `commit_id`.

3. `link_notes(source_id: str, target_id: str) -> str`
   - Adds an entry to the Links table.

4. `trace_lineage(note_id: str) -> str`
   - Returns a chronological, formatted string of all commits for a note (Timestamp, Commit ID, Message).

5. `get_graph_context(note_id: str) -> dict`
   - Returns the title and IDs of all notes that link TO and FROM the specified note.

## 5. Implementation Steps
Please execute the build in the following order:
1. Setup the Pydantic models and the SQLite initialization scripts (`db_manager.py`).
2. Implement the `diff_engine.py` logic. Write a quick unit test to ensure `apply_patch(text, create_patch(text, new_text)) == new_text`.
3. Implement `agent_tools.py` wiring the DB and Diff Engine together.
4. Output a brief `example_run.py` script that simulates the LLM calling `spawn_note`, `spawn_note`, `link_notes`, and then `evolve_note` to demonstrate the pipeline working end-to-end.

## 6. Constraints & Best Practices
- Keep dependencies minimal.
- Ensure all database queries use parameterized SQL statements to prevent injection.
- Fail gracefully: If an LLM tries to `evolve_note` on a `note_id` that doesn't exist, return a clear string error message (e.g., "Error: Note ID not found") rather than throwing a raw Python exception, so the LLM can correct its mistake.