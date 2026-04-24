"""LLM-style TUI application."""

from textual.app import App, ComposeResult

from UI.TUI.tabs.main_menu import MainMenuContainer


class TUIApp(App):
    """Main LLM TUI application."""

    def compose(self) -> ComposeResult:
        """Compose the application."""
        yield MainMenuContainer()


def main() -> int:
    """Run the LLM TUI app."""
    app = TUIApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
