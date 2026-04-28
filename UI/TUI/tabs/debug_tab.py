"""debug tab."""

import sys
from pathlib import Path

from typing import List, Dict, Optional, Any

from langgraph.constants import START
from textual.app import ComposeResult
from textual.containers import Container, HorizontalScroll, VerticalScroll
from textual.widgets import RadioSet, RadioButton, Label, TextArea, Button, Static
from UI.TUI.tabs.chat_tab import ChatTab

# Import the intent parser node
# Accessing _load_llm is intentional as it's the module's LLM factory function
from Agents.Nodes.node_intent_parser.node_IntentParser import (
    load_llm,
    evaluate_extraction,
    save_final_output,
)
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel
from typing import Annotated


class AgentGraphNode:
    """Represents a node in the visual agent execution graph."""

    def __init__(self, node_id: str, label: str, is_active: bool = False):
        self.node_id = node_id
        self.label = label
        self.is_active = is_active
        self.next_nodes: List[str] = []  # List of node ids to connect to


class GraphVisualizer(Container):
    """Component that renders a generic directed graph visually."""

    def __init__(self, nodes: List[AgentGraphNode], **kwargs: Any):
        super().__init__(**kwargs)
        self.nodes_data = nodes
        self.node_map = {n.node_id: n for n in nodes}

    def _build_layout_grid(self) -> List[List[Optional[AgentGraphNode]]]:
        """
        Organizes nodes into topological layers to create a left-to-right grid layout.
        Returns a list of columns, where each column is a list of nodes (rows).
        """
        # 1. Find root node(s) (nodes with no incoming edges)
        in_degrees: Dict[str, int] = {n.node_id: 0 for n in self.nodes_data}
        for n in self.nodes_data:
            for next_id in n.next_nodes:
                if next_id in in_degrees:
                    in_degrees[next_id] += 1

        roots = [n for n in self.nodes_data if in_degrees[n.node_id] == 0]

        # 2. Simple BFS to assign topological columns
        columns_map: Dict[str, int] = {}  # node_id -> col_index
        queue: List[tuple[str, int]] = [(root.node_id, 0) for root in roots]

        while queue:
            curr_id, col = queue.pop(0)
            if curr_id not in columns_map or columns_map[curr_id] < col:
                columns_map[curr_id] = col
                if curr_id in self.node_map:
                    for next_id in self.node_map[curr_id].next_nodes:
                        queue.append((next_id, col + 1))

        if not columns_map:
            return []

        max_col = max(columns_map.values())

        # 3. Build actual grid
        grid_cols: List[List[Optional[AgentGraphNode]]] = [
            [] for _ in range(max_col + 1)
        ]
        for node in self.nodes_data:
            if node.node_id in columns_map:
                grid_cols[columns_map[node.node_id]].append(node)

        # Pad columns so they all have the same number of rows (to form a valid grid)
        max_rows = max(len(col) for col in grid_cols) if grid_cols else 0
        for col in grid_cols:
            while len(col) < max_rows:
                col.append(None)

        return grid_cols

    def compose(self) -> ComposeResult:
        """Creates the visual representation of the agent execution graph."""
        grid = self._build_layout_grid()
        if not grid:
            yield Label("Empty Graph")
            return

        num_cols = len(grid)
        max_rows = len(grid[0]) if num_cols > 0 else 0

        # We need space for arrows between each column
        total_grid_cols = max(1, (num_cols * 2) - 1)

        with HorizontalScroll(classes="with-border", id="graph-container"):
            rs = RadioSet(classes="graph-radioset")

            # Dynamically set CSS properties for the grid
            rs.styles.layout = "grid"
            rs.styles.grid_size_columns = total_grid_cols
            rs.styles.grid_size_rows = max_rows

            # Alternate column sizes: 1fr for nodes, 6 for arrows
            col_sizes = ["1fr" if i % 2 == 0 else "6" for i in range(total_grid_cols)]
            rs.styles.grid_columns = " ".join(col_sizes)

            with rs:
                has_focus_id = False
                for r in range(max_rows):
                    for c in range(total_grid_cols):
                        is_node_col = c % 2 == 0
                        col_idx = c // 2

                        if is_node_col:
                            node = grid[col_idx][r] if r < len(grid[col_idx]) else None
                            if node:
                                if node.is_active and not has_focus_id:
                                    yield RadioButton(
                                        node.label, id="initial_focus", value=True
                                    )
                                    has_focus_id = True
                                else:
                                    yield RadioButton(node.label, value=node.is_active)
                            else:
                                yield Label("", classes="empty")
                        else:
                            # It's an arrow column between col_idx and col_idx + 1
                            curr_col_nodes = grid[col_idx]
                            next_col_nodes = grid[col_idx + 1]

                            # Are we branching from a single node to many?
                            num_curr = sum(1 for n in curr_col_nodes if n)
                            num_next = sum(1 for n in next_col_nodes if n)

                            arrow = ""

                            if num_curr == 1 and num_next > 1:
                                # Branching out
                                if r == 0:
                                    arrow = " ─┬─►"
                                elif r < num_next - 1:
                                    arrow = "  ├─►"
                                elif r == num_next - 1:
                                    arrow = "  ╰─►"
                            elif num_curr > 1 and num_next == 1:
                                # Merging in
                                if r == 0:
                                    arrow = "──┬─►"
                                elif r < num_curr - 1:
                                    arrow = "──┤  "
                                elif r == num_curr - 1:
                                    arrow = "──╯  "
                            elif num_curr == 1 and num_next == 1:
                                # 1 to 1 straight line
                                if r == 0:
                                    arrow = "  ──►"

                            yield Label(arrow, classes="arrow")


class DebugTab(Container):
    """Debug tab content."""

    DEFAULT_CSS = """
    DebugTab {
        width: 100%;
        height: 100%;
        background: $panel;
        padding: 1;
    }
    
    .with-border {
        border: round $primary;
        border-title-color: $text;
        background: $surface;
        padding: 1 2;
    }
    
    #graph-container {
        height: auto;
        min-height: 15;
    }
    
    .graph-radioset {
        border: none;
        background: transparent;
        width: auto;
    }
    
    RadioButton {
        padding: 0 1;
        height: 3;
    }
    
    .arrow {
        content-align: center middle;
        color: $text-muted;
        text-style: bold;
        height: 3;
    }
    
    .empty {
        width: 100%;
        height: 100%;
    }
    
    .input-label {
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
        height: 1;
    }
    
    .output-label {
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
        height: 1;
    }
    
    .input-area, .output-area {
        height: 8;
        border: solid $primary;
        margin-bottom: 1;
    }
    
    #parse-button {
        margin: 1 0;
        width: 20;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the memory visualizer."""


        # Define standard graph nodes and their connections
        n_start = AgentGraphNode("start", "START", is_active=True)
        n_intent = AgentGraphNode("intent", "Intent Parser")
        n_task = AgentGraphNode("task", "Task Master")

        # Parallel actions
        n_web = AgentGraphNode("web", "Action: Web")
        n_rag = AgentGraphNode("rag", "Action: RAG")
        n_code = AgentGraphNode("code", "Action: Code")

        n_eval = AgentGraphNode("eval", "Evaluation")
        n_end = AgentGraphNode("end", "END")

        # Build graph topology (Edges)
        n_start.next_nodes = ["intent"]
        n_intent.next_nodes = ["task"]
        n_task.next_nodes = ["web", "rag", "code"]  # Task splits into 3

        n_web.next_nodes = ["eval"]  # All 3 merge into eval
        n_rag.next_nodes = ["eval"]
        n_code.next_nodes = ["eval"]

        n_eval.next_nodes = ["end"]

        nodes = [n_start, n_intent, n_task, n_web, n_rag, n_code, n_eval, n_end]

        with VerticalScroll() as scroll:
            scroll.border_title = "Agent Execution Graph (LangGraph States)"
            yield ChatTab()  # Reuse chat tab for debug here
            yield Static("Input Text:", classes="input-label")
            yield TextArea(
                id="intent-input",
                placeholder="Enter text for intent parsing...",
                classes="input-area",
            )
            yield Button("Parse Intent", id="parse-button", variant="primary")
            yield Static("Output:", classes="output-label")
            yield TextArea(id="intent-output", read_only=True, classes="output-area")

            yield Static("Daha Fonksiyonel Değil:", classes="output-label")
            yield GraphVisualizer(nodes)

    def on_mount(self) -> None:
        """Initialize the debug tab."""
        try:
            self.query_one("#initial_focus", RadioButton).focus()
        except Exception as e:
            self.log(f"Could not focus initial node: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "parse-button":
            self.parse_intent_from_ui()

    def parse_intent_from_ui(self) -> None:
        """Parse intent from UI input instead of file."""
        try:
            # Get input text from the text area
            input_text_area = self.query_one("#intent-input", TextArea)
            input_text = input_text_area.text.strip()

            if not input_text:
                self.notify("Please enter some text to parse", severity="warning")
                return

            # Add the Agents directory to the path so we can import the intent parser
            agents_path = Path(__file__).parents[3] / "Agents"
            sys.path.insert(0, str(agents_path))

            # ----------------------------------------
            # ----------------------------------------

            # Override the read_input_file function to use our UI input
            def read_ui_input() -> str:
                """Reads the input text from UI and returns its content. Call this first to get context."""
                return input_text

            # Create a custom agent that uses our UI input
            def build_custom_agent():
                """Builds a custom agent that uses UI input instead of file input."""
                tools = [read_ui_input, evaluate_extraction, save_final_output]
                tool_node = ToolNode(tools)
                llm_with_tools = load_llm().bind_tools(tools)

                system_prompt = SystemMessage(
                    content="""You are an autonomous Intent Parsing Agent equipped with file and evaluation tools. 
                Your strict workflow is:
                1. Call `read_input_file` to fetch the source text.
                2. Analyze the text and extract the required parameters.
                3. Call `evaluate_extraction` to critique your own extraction.
                4. If critique is given, adjust and call `evaluate_extraction` again.
                5. Only when 'PASS' is returned, call `save_final_output` to save.
                6. Conclude the workflow.
                """
                )

                # Strongly typed Node function
                def call_model(state: AgentState) -> Dict[str, list[BaseMessage]]:
                    """Processes the current state and returns the LLM's response."""
                    messages = state.messages
                    if not any(isinstance(m, SystemMessage) for m in messages):
                        messages = [system_prompt] + messages

                    response = llm_with_tools.invoke(messages)
                    return {"messages": [response]}

                # Initialize Graph with the standard TypedDict
                workflow = StateGraph(AgentState)

                workflow.add_node("agent", call_model)
                workflow.add_node("tools", tool_node)

                workflow.add_edge(START, "agent")
                workflow.add_conditional_edges("agent", tools_condition)
                workflow.add_edge("tools", "agent")

                return workflow.compile()

            # Define the AgentState (copied from the original)
            class AgentState(BaseModel):
                """State model for the intent parsing agent."""

                messages: Annotated[list[BaseMessage], add_messages]

            # Run the agent
            self.notify("Parsing intent...", severity="information")
            graph = build_custom_agent()

            graph.invoke(
                {
                    "messages": [
                        (
                            "user",
                            "Start the pipeline: Read the input file, evaluate your intent extraction until it passes, and write to output.",
                        )
                    ]
                }
            )

            # Check the output file for results
            output_file = (
                Path(__file__).parents[3]
                / "Agents"
                / "Nodes"
                / "node_intent_parser"
                / "Output.txt"
            )
            if output_file.exists():
                output_text = output_file.read_text(encoding="utf-8")
                output_area = self.query_one("#intent-output", TextArea)
                output_area.text = output_text
                self.notify("Intent parsed successfully!", severity="information")
            else:
                self.notify(
                    "Failed to parse intent - no output generated", severity="error"
                )

        except Exception as e:
            self.notify(f"Error parsing intent: {str(e)}", severity="error")
            self.log(f"Error in parse_intent_from_ui: {e}")
