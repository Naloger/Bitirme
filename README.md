# Design Project

A cognitive architecture system integrating Jungian psychology, Adlerian psychology, Zettelkasten methodology, Concurrent Task Trees (CTT), and graph-triplet knowledge bases for AI agents.

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    UI/TUI                           │
│  (Textual-based Terminal User Interface)            │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                   Agents                            │
│  (LangGraph-based agent nodes)                      │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                  Data/DataTypes                     │
│  (Psychology-aware data structures)                 │
└─────────────────────────────────────────────────────┘
```

## Project Structure

### UI/TUI/
Terminal User Interface built with [Textual](https://textual.textualize.io/).

| File | Description |
|------|-------------|
| `tui_app.py` | Main TUI application entry point |
| `tabs/main_menu.py` | Tabbed navigation container |
| `tabs/chat_tab.py` | Chat interface tab |
| `tabs/graph_visualizer.py` | Graph state visualization |
| `tabs/memory_visualizer.py` | Memory/knowledge visualization |
| `tabs/configure.py` | Configuration settings |
| `tabs/debug_tab.py` | Debug and inspection tools |

### Data/DataTypes/
Psychology-aware data structures for the cognitive architecture.

| Path | Description |
|------|-------------|
| `PageTypes/` | Zettelkasten-style page structures |
| `TheSelfTypes/` | Jungian psychology types (Self, Shadow, Ego, Animus) |
| `EvergreenTypes/` | Growth/versioned entity types |

#### PageTypes
- `Page` - Base Zettelkasten page with UUID and timestamps
- `page_structured.py` - Structured page format
- `page_unstructured.py` - Unstructured/raw page format

#### TheSelfTypes
- `self.py` - The totality of psyche (Jungian Self)
- `shadow.py` - Shadow archetype (unconscious aspects)
- `ego.py` - Ego structure
- `anim.py` - Anima/Animus archetype

#### EvergreenTypes
- `evergreen_Seed.py` - Initial idea/seed
- `evergreen_Sapling.py` - Growing idea
- `evergreen_Tree.py` - Mature interconnected knowledge

### Agents/
LangGraph-based agent nodes for task execution and cognition.

| Agent | Description |
|------|-------------|
| `node_intent_parser/` | Parses user intent with quality evaluation tools |
| `node_task_master/` | Task orchestration and management |
| `node_lemmatizer/` | Text lemmatization for NLP |
| `node_stream_guard/` | Loop/infinite iteration guard |
| `node_textgraph/` | Graph-based text operations |
| `node_template/` | Base template for new agents |

## Core Concepts

### Psychological Framework
- **Jungian**: Archetypes (Hero, Shadow, Wise Old Man, Anima/Animus, Self)
- **Adlerian**: Goal-oriented attention, striving toward superiority

### Knowledge Management
- **Zettelkasten**: Atomic, versioned, interconnected notes
- **Graph Triplets**: Entity-Relation-Entity knowledge representation

### Task Execution
- **CTT**: Concurrent Task Trees for hierarchical decomposition
- **Agent Orchestration**: LangGraph-based multi-agent coordination

## Dependencies

- `langchain-core`
- `langgraph`
- `langchain-ollama`
- `textual`
- `pydantic`
- `ollama` (local LLM)

## Configuration

LLM configuration is managed via `llm_config.json` at the project root.

## Running the TUI

```bash
python run_TUI.py
```
