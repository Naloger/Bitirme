"""Memory Visualizer tab."""
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import RichLog


class DebugTab(Container):
    """Debug tab content."""

    DEFAULT_CSS = """
    DebugTab {
        width: 100%;
        height: 100%;
        background: $panel;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the memory visualizer."""
        yield RichLog(id="debug-log", markup=True)

    def on_mount(self) -> None:
        """Initialize the debug tab."""
        memory_log = self.query_one("#debug-log", RichLog)
        memory_log.write("[bold cyan]Debug Tab[/bold cyan]\n")
        memory_log.write("[dim]??? Not Added Yet .[/dim]\n")
        memory_log.write("[yellow]• Ready to debug ?[/yellow]\n")

