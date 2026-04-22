"""Configure tab."""
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import RichLog


class Configure(Container):
    """Configure tab content."""

    DEFAULT_CSS = """
    Configure {
        width: 100%;
        height: 100%;
        background: $panel;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the configure tab."""
        yield RichLog(id="config-log", markup=True)

    def on_mount(self) -> None:
        """Initialize the configure tab."""
        config_log = self.query_one("#config-log", RichLog)
        config_log.write("[bold cyan]Configuration Settings[/bold cyan]\n")
        config_log.write("[dim]Configuration options will be available here[/dim]\n")
        config_log.write("[yellow]• Ready to configure application settings[/yellow]\n")

