# Nodes Workflow Guide: Integration with TUI and LangGraph

This guide explains how to use the existing LangGraph nodes, connect them together into workflows, and integrate them with the Textual TUI application.

---

## Overview of Available Nodes

### 1. **node_task_master** — Task Decomposition
- **Purpose**: Converts natural language user input into Concurrent Task Trees (CTT) JSON structure
- **Input**: User prompt/goal description (string)
- **Output**: Structured CTT task JSON with operators (sequence, choice, interleaving, disabling)
- **State Fields**:
  - `input_text`: User prompt
  - `output_text`: Generated CTT JSON
  - `ctt_state`: Parsed CTT state dict
  - `validation_errors`: Any validation issues
  - `raw_response_text`: Raw LLM response
  - `model`: Model name used

**Example**:
```python
from Agents.Nodes.node_task_master.node_TaskMaster import TaskMasterState, task_master_node

state = TaskMasterState(
    input_text="Summarize the paper and create a presentation",
    model="gemma4-e2b-128k:latest"
)
result = task_master_node(state)
# result.output_text contains CTT JSON:
# { "type": "sequence", "tasks": [...] }
```

---

### 2. **node_stream_guard** — Streaming with Loop Detection
- **Purpose**: Calls Ollama API with streaming, detects repetitive loops, cuts off and restarts with feedback
- **Input**: Prompt text, optional message history
- **Output**: Final generated text (with loop protection)
- **State Fields**:
  - `input_text`: Prompt to send
  - `output_text`: Final response
  - `thinking_text`: Extracted reasoning (if model supports thinking)
  - `loop_restarts`: How many times loop was detected
  - `messages`: Conversation history (list of role/content dicts)

**Key Feature**: Detects when model is repeating itself and injects feedback to refocus.

**Example**:
```python
from Agents.Nodes.node_stream_guard.node_LoopGuard import StreamGuardState, stream_guard_node

state = StreamGuardState(
    input_text="Explain quantum computing in detail",
    messages=[]
)
result = stream_guard_node(state)
print(f"Output: {result.output_text}")
print(f"Loop detections: {result.loop_restarts}")
```

---

### 3. **node_lemmatizer** — NLP Text Preprocessing
- **Purpose**: Lemmatizes text in multiple languages (Turkish, English, Multilingual fallback)
- **Input**: Raw text string
- **Output**: Lemmatized text, word counts, detected language
- **State Fields**:
  - `raw_text`: Input text
  - `tokens`: Tokenized words
  - `lemmatized_tokens`: After lemmatization
  - `detected_language`: "tr", "en", or "unknown"
  - `output_text`: Formatted result

**Supports**:
- Turkish (Stanza pipeline)
- English (spaCy)
- Fallback (NLTK wordnet)

**Example**:
```python
from Agents.Nodes.node_lemmatizer.node_Lemmatize import LemmatizeState, lemmatize_graph

state = LemmatizeState(raw_text="The systems are running quickly")
graph = lemmatize_graph()
result = graph.invoke(state)
print(result["output_text"])  # "the system be run quick"
```

---

### 4. **node_textgraph** — Word Co-occurrence Graph
- **Purpose**: Builds a semantic graph from text (words as nodes, co-occurrence as edges)
- **Input**: Raw text
- **Output**: Graph structure (nodes, edges) and formatted output
- **State Fields**:
  - `raw_text`: Input text
  - `tokens`: Tokenized words
  - `nodes`: Dict mapping word → id
  - `edges`: Dict mapping "word1|word2" → co-occurrence weight
  - `output_text`: Formatted graph in text form
  - `window`: Co-occurrence window size (default 2)

**Example**:
```python
from Agents.Nodes.node_textgraph.node import WordGraphState, build_word_graph

state = WordGraphState(
    raw_text="Machine learning is powerful learning technique",
    window=2
)
graph = build_word_graph()
result = graph.invoke(state)
# result["edges"] = {"machine|learning": 2, "learning|powerful": 1, ...}
```

---

## Connecting Nodes into Workflows

### Pattern 1: Linear Pipeline (Chat → TaskMaster → LLM Execution)

```python
from langgraph.graph import START, END, StateGraph
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class WorkflowState(BaseModel):
    """Unified state for the entire workflow."""
    user_input: str = ""
    task_tree: Dict[str, Any] = Field(default_factory=dict)
    llm_response: str = ""
    lemmatized_text: str = ""
    graph_output: str = ""
    errors: List[str] = Field(default_factory=list)


def node_parse_task(state: WorkflowState) -> Dict[str, Any]:
    """Step 1: Parse user input into task tree."""
    from Agents.Nodes.node_task_master.node_TaskMaster import task_master_node, TaskMasterState
    
    task_state = TaskMasterState(input_text=state.user_input)
    result = task_master_node(task_state)
    
    return {
        "task_tree": result.ctt_state,
        "errors": state.errors + result.validation_errors if result.validation_errors else state.errors
    }


def node_process_with_llm(state: WorkflowState) -> Dict[str, Any]:
    """Step 2: Send task description to LLM with loop guard."""
    from Agents.Nodes.node_stream_guard.node_LoopGuard import stream_guard_node, StreamGuardState
    
    prompt = f"Execute this task:\n{state.task_tree.get('description', state.user_input)}"
    stream_state = StreamGuardState(input_text=prompt)
    result = stream_guard_node(stream_state)
    
    return {
        "llm_response": result.output_text,
        "errors": state.errors + ([f"Loop detected {result.loop_restarts} times"] if result.loop_restarts > 0 else [])
    }


def node_analyze_response(state: WorkflowState) -> Dict[str, Any]:
    """Step 3: Lemmatize and build graph from LLM response."""
    from Agents.Nodes.node_lemmatizer.node_Lemmatize import lemmatize_graph, LemmatizeState
    from Agents.Nodes.node_textgraph.node import build_word_graph, WordGraphState
    
    # Lemmatize
    lem_state = LemmatizeState(raw_text=state.llm_response)
    lemma_graph = lemmatize_graph()
    lem_result = lemma_graph.invoke(lem_state)
    
    # Build word graph
    graph_state = WordGraphState(raw_text=state.llm_response)
    word_graph = build_word_graph()
    graph_result = word_graph.invoke(graph_state)
    
    return {
        "lemmatized_text": lem_result["output_text"],
        "graph_output": graph_result["output_text"]
    }


# Compose workflow
def build_workflow():
    """Assemble all nodes into a LangGraph."""
    builder = StateGraph(WorkflowState)
    
    # Add nodes
    builder.add_node("parse_task", node_parse_task)
    builder.add_node("process_llm", node_process_with_llm)
    builder.add_node("analyze", node_analyze_response)
    
    # Define edges
    builder.add_edge(START, "parse_task")
    builder.add_edge("parse_task", "process_llm")
    builder.add_edge("process_llm", "analyze")
    builder.add_edge("analyze", END)
    
    return builder.compile()


# Run
workflow = build_workflow()
initial_state = WorkflowState(user_input="Analyze the sentiment of this paper and create a summary")
result = workflow.invoke(initial_state)
print(result)
```

---

### Pattern 2: Branching Workflow (CTT-based Multi-Task Dispatch)

```python
class MultiTaskState(BaseModel):
    """State for multi-task workflow driven by CTT."""
    user_input: str = ""
    ctt_tree: Dict[str, Any] = Field(default_factory=dict)
    task_results: List[Dict[str, Any]] = Field(default_factory=list)
    final_output: str = ""


def node_decompose_and_route(state: MultiTaskState) -> Dict[str, Any]:
    """Parse user input and extract individual tasks."""
    from Agents.Nodes.node_task_master.node_TaskMaster import task_master_node, TaskMasterState
    
    task_state = TaskMasterState(input_text=state.user_input)
    result = task_master_node(task_state)
    
    return {"ctt_tree": result.ctt_state}


def node_execute_task_sequence(state: MultiTaskState) -> Dict[str, Any]:
    """Execute multiple tasks in sequence based on CTT."""
    from Agents.Nodes.node_stream_guard.node_LoopGuard import stream_guard_node, StreamGuardState
    
    tasks = state.ctt_tree.get("tasks", [])
    results = []
    
    for task in tasks:
        prompt = task.get("description", "")
        stream_state = StreamGuardState(input_text=prompt)
        result = stream_guard_node(stream_state)
        results.append({
            "task": task.get("id"),
            "result": result.output_text,
            "loop_count": result.loop_restarts
        })
    
    return {"task_results": results}


def node_synthesize_results(state: MultiTaskState) -> Dict[str, Any]:
    """Combine all task results into final output."""
    combined = "\n---\n".join([
        f"Task {r['task']}:\n{r['result']}" 
        for r in state.task_results
    ])
    
    return {"final_output": combined}


# Build branching workflow
def build_multitask_workflow():
    builder = StateGraph(MultiTaskState)
    
    builder.add_node("decompose", node_decompose_and_route)
    builder.add_node("execute", node_execute_task_sequence)
    builder.add_node("synthesize", node_synthesize_results)
    
    builder.add_edge(START, "decompose")
    builder.add_edge("decompose", "execute")
    builder.add_edge("execute", "synthesize")
    builder.add_edge("synthesize", END)
    
    return builder.compile()
```

---

## Integration with TUI

### 1. Add a "Workflow" Tab

Create `UI/TUI/tabs/workflow_runner.py`:

```python
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import Button, Input, RichLog, Select, Static

from llm_config import load_llm_config


class WorkflowRunner(VerticalScroll):
    """Workflow execution tab."""
    
    DEFAULT_CSS = """
    WorkflowRunner {
        width: 100%;
        height: 100%;
        layout: vertical;
        overflow-y: auto;
    }
    
    WorkflowRunner #workflow-selector {
        width: 100%;
        height: auto;
        margin-bottom: 1;
        border: solid $accent;
        padding: 1;
    }
    
    WorkflowRunner #workflow-log {
        width: 100%;
        height: 1fr;
        border: solid $accent;
        background: $surface;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Container(id="workflow-selector"):
            yield Static("Select Workflow:", classes="label")
            yield Select(
                options=[
                    ("Linear: Task → LLM → Analyze", "linear"),
                    ("Multi-Task with CTT", "multitask"),
                    ("Lemmatize + Graph Analysis", "lemmatize_graph"),
                ],
                value="linear",
                id="workflow-choice",
            )
            yield Input(
                placeholder="Enter your input...",
                id="workflow-input",
            )
            with Horizontal():
                yield Button("Run Workflow", id="run-button", variant="primary")
                yield Button("Clear", id="clear-button", variant="warning")
        
        yield RichLog(id="workflow-log", markup=True)
    
    def on_mount(self) -> None:
        self.query_one("#workflow-log", RichLog).write(
            "[bold cyan]Workflow Runner[/bold cyan]\n"
            "[dim]Select workflow, enter input, and click Run[/dim]\n\n"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-button":
            self._run_workflow()
        elif event.button.id == "clear-button":
            self.query_one("#workflow-log", RichLog).clear()
    
    def _run_workflow(self) -> None:
        from textual import work
        
        workflow_choice = self.query_one("#workflow-choice", Select).value
        user_input = self.query_one("#workflow-input", Input).value.strip()
        log = self.query_one("#workflow-log", RichLog)
        
        if not user_input:
            log.write("[bold red]Error:[/bold red] Enter input first\n")
            return
        
        log.write(f"[yellow]Running {workflow_choice}...[/yellow]\n")
        self._execute_workflow_worker(workflow_choice, user_input)
    
    @work(thread=True)
    def _execute_workflow_worker(self, workflow_choice: str, user_input: str) -> None:
        from Agents.Nodes.WORKFLOW_EXAMPLES import (
            build_workflow, 
            build_multitask_workflow,
            build_lemmatize_graph_workflow,
            WorkflowState
        )
        
        try:
            if workflow_choice == "linear":
                workflow = build_workflow()
                state = WorkflowState(user_input=user_input)
            elif workflow_choice == "multitask":
                workflow = build_multitask_workflow()
                state = WorkflowState(user_input=user_input)
            else:
                workflow = build_lemmatize_graph_workflow()
                state = WorkflowState(user_input=user_input)
            
            result = workflow.invoke(state)
            
            output = f"""
[green]Workflow Complete[/green]
            
Task Tree:
{result.get('task_tree', 'N/A')}

LLM Response:
{result.get('llm_response', 'N/A')[:500]}...

Analysis:
{result.get('lemmatized_text', 'N/A')[:300]}...

Graph:
{result.get('graph_output', 'N/A')[:300]}...

Errors: {result.get('errors', [])}
            """
            
            self.app.call_from_thread(self._log_result, output)
            
        except Exception as exc:
            self.app.call_from_thread(self._log_error, str(exc))
    
    def _log_result(self, output: str) -> None:
        self.query_one("#workflow-log", RichLog).write(output)
    
    def _log_error(self, error: str) -> None:
        self.query_one("#workflow-log", RichLog).write(
            f"[bold red]Execution Error:[/bold red] {error}\n"
        )
```

### 2. Register Workflow Tab in TUI

Update `UI/TUI/tabs/main_menu.py`:

```python
from UI.TUI.tabs.workflow_runner import WorkflowRunner

# In MainMenuContainer.compose():
with ContentSwitcher(initial="panel_chat", id="llm-main"):
    # ... existing tabs ...
    
    # New Workflow Tab
    with Container(id="panel_workflow", classes="tab-panel"):
        yield WorkflowRunner()

# In TAB_TO_PANEL dict:
TAB_TO_PANEL = {
    "tab_chat": "panel_chat",
    "tab_graph": "panel_graph",
    "tab_memory": "panel_memory",
    "tab_config": "panel_config",
    "tab_workflow": "panel_workflow",  # NEW
}

# In compose(), add tab:
yield Tab("Workflow", id="tab_workflow"),
```

---

## Full Workflow Example: Chat Integration

### Trigger from Chat Tab

In `UI/TUI/tabs/chat_tab.py`, add workflow invocation on special commands:

```python
def _send_message(self) -> None:
    """Send message and optionally trigger workflow."""
    input_widget = self.query_one("#message-input", Input)
    chat_log = self.query_one("#chat-messages", RichLog)
    
    message = input_widget.value.strip()
    if not message:
        return
    
    chat_log.write(f"[bold blue]You:[/bold blue] {message}\n")
    input_widget.value = ""
    
    # Special command: /workflow <type> <input>
    if message.startswith("/workflow"):
        self._handle_workflow_command(message)
    else:
        # Normal chat
        self._set_chat_busy(True)
        chat_log.write("[bold green]Assistant:[/bold green] [dim]Thinking...[/dim]\n")
        self._invoke_llm_worker(message)
    
    input_widget.focus()


def _handle_workflow_command(self, message: str) -> None:
    """Execute a workflow from chat command."""
    parts = message.split(maxsplit=2)
    if len(parts) < 3:
        self._log_chat("[bold red]Usage:[/bold red] /workflow <linear|multitask> <input>")
        return
    
    workflow_type = parts[1]
    user_input = parts[2]
    
    self._log_chat(f"[yellow]Executing {workflow_type} workflow...[/yellow]")
    self._invoke_workflow_worker(workflow_type, user_input)


@work(thread=True)
def _invoke_workflow_worker(self, workflow_type: str, user_input: str) -> None:
    """Run workflow in background thread."""
    from Agents.Nodes.WORKFLOW_EXAMPLES import build_workflow, WorkflowState
    
    try:
        workflow = build_workflow()
        state = WorkflowState(user_input=user_input)
        result = workflow.invoke(state)
        
        output = f"""
[green]✓ Workflow Complete[/green]

**Task Tree:**
{str(result.get('task_tree', {}))[:200]}

**LLM Response:**
{result.get('llm_response', '')[:300]}...

**Graph Analysis:**
{result.get('graph_output', '')[:200]}...
        """
        
        self.app.call_from_thread(self._on_workflow_result, output)
    except Exception as exc:
        self.app.call_from_thread(self._on_workflow_error, str(exc))


def _on_workflow_result(self, output: str) -> None:
    chat_log = self.query_one("#chat-messages", RichLog)
    chat_log.write(output + "\n\n")
    self.query_one("#message-input", Input).focus()


def _on_workflow_error(self, error: str) -> None:
    chat_log = self.query_one("#chat-messages", RichLog)
    chat_log.write(f"[bold red]Workflow Error:[/bold red] {error}\n\n")
    self.query_one("#message-input", Input).focus()


def _log_chat(self, message: str) -> None:
    chat_log = self.query_one("#chat-messages", RichLog)
    chat_log.write(message + "\n")
```

---

## Advanced: Graph Visualization

Show CTT task tree and word graphs in "Graph" tab:

```python
# In UI/TUI/tabs/graph_visualizer.py

from UI.TUI.tabs.graph_visualizer import GraphVisualizer

class GraphVisualizer(Container):
    def _render_ctt_tree(self, ctt_state: dict) -> str:
        """Convert CTT state to ASCII tree."""
        def render_node(node, depth=0):
            indent = "  " * depth
            operator = node.get("operator", "task")
            tasks = node.get("tasks", [])
            
            lines = [f"{indent}[{operator}]"]
            for task in tasks:
                lines.append(render_node(task, depth + 1))
            return "\n".join(lines)
        
        return render_node(ctt_state)
    
    def _render_word_graph(self, edges: dict) -> str:
        """Convert edge dict to ASCII graph visualization."""
        lines = ["Word Co-occurrence Graph:"]
        for edge, weight in sorted(edges.items(), key=lambda x: -x[1])[:10]:
            word1, word2 = edge.split("|")
            lines.append(f"  {word1} -> {word2} ({weight})")
        return "\n".join(lines)
```

---

## State Flow Diagram

```
┌─────────────┐
│ User Input  │  (Chat tab or /workflow command)
└──────┬──────┘
       │
       ▼
┌──────────────────────┐
│  TaskMaster Node     │  Parse into CTT structure
│  Decomposes goal     │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ StreamGuard Node     │  LLM processing with loop detection
│ Calls Ollama API     │
└──────┬───────────────┘
       │
       ├─────────────────────────┐
       │                         │
       ▼                         ▼
┌──────────────────┐      ┌──────────────────┐
│ Lemmatizer Node  │      │ TextGraph Node   │
│ NLP Analysis     │      │ Co-occurrence    │
└──────┬───────────┘      └──────┬───────────┘
       │                         │
       └─────────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  UI Display          │
          │  Chat/Graph/Results  │
          └──────────────────────┘
```

---

## Summary: Node Usage Checklist

- [ ] Import desired nodes from `Agents/Nodes/`
- [ ] Create workflow state class (dict or Pydantic model)
- [ ] Define node functions that read state and return updated dict
- [ ] Build LangGraph: `StateGraph(State)` → `.add_node()` → `.add_edge()` → `.compile()`
- [ ] Invoke: `graph.invoke(initial_state)`
- [ ] Display results in TUI tab (RichLog)
- [ ] Handle errors and edge cases (exceptions, empty inputs)
- [ ] Optional: Stream results back to chat tab via `@work(thread=True)` + `call_from_thread()`

---

## Common Patterns

### Pattern: Conditional Routing
```python
def conditional_node(state):
    if "urgent" in state.user_input.lower():
        return {"workflow_type": "fast_track"}
    else:
        return {"workflow_type": "standard"}
```

### Pattern: Aggregating Results
```python
def aggregate_node(state):
    results = []
    for item in state.task_results:
        results.append(item["llm_response"])
    return {"final_summary": "\n".join(results)}
```

### Pattern: Error Handling
```python
def safe_node(state):
    try:
        result = potentially_failing_operation(state)
        return {"output": result}
    except Exception as e:
        return {"errors": state.errors + [str(e)]}
```

---

## Next Steps

1. **Create workflow module**: `Agents/Nodes/WORKFLOW_EXAMPLES.py` with reusable graph definitions
2. **Add workflow runner tab** to TUI main_menu
3. **Integrate** with chat tab commands (`/workflow <type> <input>`)
4. **Add graph visualization** for CTT trees and word graphs
5. **Extend with feedback loop**: Save workflow results to Zettelkasten vault for future reference

