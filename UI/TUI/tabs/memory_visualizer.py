"""Memory Visualizer tab."""
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import RichLog


class MemoryVisualizer(Container):
    """Memory Visualizer tab content."""

    DEFAULT_CSS = (Path(__file__).parent / "css" / "memory_visualizer.tcss").read_text(
        encoding="utf-8"
    )
    def compose(self) -> ComposeResult:
        """Compose the memory visualizer."""
        yield RichLog(id="memory-log", markup=True)

    def on_mount(self) -> None:
        """Initialize the memory visualizer."""
        memory_log = self.query_one("#memory-log", RichLog)
        memory_log.write("[bold cyan]Memory Visualizer[/bold cyan]\n")
        memory_log.write(
            "[dim]Memory usage and cache information will be displayed here[/dim]\n"
        )
        memory_log.write("[yellow]• Ready to monitor memory statistics[/yellow]\n")
