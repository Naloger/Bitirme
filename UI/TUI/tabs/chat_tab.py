"""Chat tab with ChatGPT-like UI."""
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, Input, RichLog


class ChatTab(Container):
    """Chat tab content with ChatGPT-like interface."""

    DEFAULT_CSS = """
    ChatTab {
        width: 100%;
        height: 90%;
        layout: vertical;
        background: $panel;
    }

    ChatTab #chat-messages {
        width: 100%;
        height: 1fr;
        border: solid $accent;
        background: $surface;
    }

    ChatTab #chat-input-area {
        width: 100%;
        height: auto;
        border-top: solid $accent;
        background: $panel;
        padding: 1;
        layout: vertical;
    }

    ChatTab #message-input {
        width: 100%;
        height: 3;
        border: solid $accent;
        margin-bottom: 1;
    }

    ChatTab #button-container {
        width: 100%;
        height: auto;
        layout: horizontal;
    }

    ChatTab Button {
        width: 1fr;
        height: 3;
        margin: 0 1;
        content-align: center middle;
        text-align: center;
    }

    ChatTab #send-button {
        background: $accent;
        color: white;
    }

    ChatTab #send-button:hover {
        background: $boost;
    }

    ChatTab #clear-button {
        background: $warning;
        color: white;
    }

    ChatTab #clear-button:hover {
        background: $error;
    }

    ChatTab Static {
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the chat tab."""
        # Messages display area
        yield RichLog(id="chat-messages", markup=True)

        # Input area
        with Container(id="chat-input-area"):
            yield Input(
                placeholder="Type your message here...",
                id="message-input",
            )

            # Buttons container
            with Horizontal(id="button-container"):
                yield Button("Send", id="send-button", variant="primary")
                yield Button("🗑Clear", id="clear-button", variant="warning")

    def on_mount(self) -> None:
        """Initialize the chat tab."""
        chat_log = self.query_one("#chat-messages", RichLog)
        chat_log.write("[bold cyan]🤖 LLM Chat Assistant[/bold cyan]\n")
        chat_log.write("[dim]Welcome to the LLM Chat Interface[/dim]\n")
        chat_log.write("[yellow]• Type your message and click Send[/yellow]\n")
        chat_log.write("[yellow]• Use Clear to reset the conversation[/yellow]\n\n")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "send-button":
            self._send_message()
        elif event.button.id == "clear-button":
            self._clear_chat()

    def _send_message(self) -> None:
        """Send a message to the chat."""
        input_widget = self.query_one("#message-input", Input)
        chat_log = self.query_one("#chat-messages", RichLog)

        message = input_widget.value.strip()
        if not message:
            return

        # Display user message
        chat_log.write(f"[bold blue]You:[/bold blue] {message}\n")

        # Clear input
        input_widget.value = ""

        # Placeholder for LLM response
        chat_log.write(
            "[bold green]Assistant:[/bold green] "
            "[dim]Awaiting response from LLM...[/dim]\n\n"
        )

        # Focus back to input
        input_widget.focus()

    def _clear_chat(self) -> None:
        """Clear all chat messages."""
        chat_log = self.query_one("#chat-messages", RichLog)
        chat_log.clear()
        chat_log.write("[bold cyan]LLM Chat Assistant[/bold cyan]\n")
        chat_log.write("[dim]Conversation cleared[/dim]\n\n")
        self.query_one("#message-input", Input).focus()

