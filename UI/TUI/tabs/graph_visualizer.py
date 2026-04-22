"""Graph State Visualizer tab."""
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import RichLog


class GraphVisualizer(Container):
    """Graph State Visualizer tab content."""

    DEFAULT_CSS = """
    GraphVisualizer {
        width: 100%;
        height: 100%;
        background: $panel;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the graph visualizer."""
        yield RichLog(id="graph-log", markup=True)

    def on_mount(self) -> None:
        """Initialize the graph visualizer."""
        graph_log = self.query_one("#graph-log", RichLog)
        graph_log.write("[bold cyan]Graph State Visualizer[/bold cyan]\n")
        graph_log.write("[dim]State transitions and graph structure will be displayed here[/dim]\n")
        graph_log.write("[yellow]• Ready to visualize state graphs[/yellow]\n")

