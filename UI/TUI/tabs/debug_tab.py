"""debug tab."""

from typing import List, Dict, Optional, Any
from textual.app import ComposeResult
from textual.containers import Container, HorizontalScroll, VerticalScroll
from textual.widgets import RadioSet, RadioButton, Label
from UI.TUI.tabs.chat_tab import ChatTab


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
    """

    def compose(self) -> ComposeResult:
        """Compose the memory visualizer."""

        # Define standard graph nodes and their connections
        n_start = AgentGraphNode("start", "START", is_active=True)
        n_task = AgentGraphNode("task", "Task Master")

        # Parallel actions
        n_web = AgentGraphNode("web", "Action: Web")
        n_rag = AgentGraphNode("rag", "Action: RAG")
        n_code = AgentGraphNode("code", "Action: Code")

        n_eval = AgentGraphNode("eval", "Evaluation")
        n_end = AgentGraphNode("end", "END")

        # Build graph topology (Edges)
        n_start.next_nodes = ["task"]
        n_task.next_nodes = ["web", "rag", "code"]  # Task splits into 3

        n_web.next_nodes = ["eval"]  # All 3 merge into eval
        n_rag.next_nodes = ["eval"]
        n_code.next_nodes = ["eval"]

        n_eval.next_nodes = ["end"]

        nodes = [n_start, n_task, n_web, n_rag, n_code, n_eval, n_end]

        with VerticalScroll() as scroll:
            scroll.border_title = "Agent Execution Graph (LangGraph States)"
            yield ChatTab()  # Reuse chat tab for debug here
            yield GraphVisualizer(nodes)

    def on_mount(self) -> None:
        """Initialize the debug tab."""
        try:
            self.query_one("#initial_focus", RadioButton).focus()
        except Exception as e:
            self.log(f"Could not focus initial node: {e}")
