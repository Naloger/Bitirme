"""Chat tab with ChatGPT-like UI."""
from typing import Any

from llm_config import ConfigError, load_llm_config
from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, Input, RichLog
from langchain_ollama import ChatOllama


class ChatTab(Container):
    """Chat tab content with ChatGPT-like interface."""

    _llm: Any = None
    _llm_error: str | None = None

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
                yield Button("Clear", id="clear-button", variant="warning")

    def on_mount(self) -> None:
        """Initialize the chat tab."""
        chat_log = self.query_one("#chat-messages", RichLog)
        chat_log.write("[bold cyan]LLM Chat Assistant[/bold cyan]\n")
        chat_log.write("[dim]Welcome to the LLM Chat Interface[/dim]\n")
        chat_log.write("[yellow]• Type your message and click Send[/yellow]\n")
        chat_log.write("[yellow]• Use Clear to reset the conversation[/yellow]\n\n")

        self._initialize_llm()

    def _initialize_llm(self) -> None:
        """Create a local Ollama chat client from JSON config."""
        chat_log = self.query_one("#chat-messages", RichLog)
        self._llm = None
        self._llm_error = None

        try:
            config = load_llm_config()
            ollama_cfg = config.raw.get("ollama", {})
            timeout_seconds = ollama_cfg.get("timeout_seconds", 300)
            client_kwargs = {"timeout": timeout_seconds} if timeout_seconds else {}
            self._llm = ChatOllama(
                model=str(ollama_cfg.get("model", "")).strip(),
                base_url=str(ollama_cfg.get("base_url", "http://127.0.0.1:11434")).strip(),
                temperature=ollama_cfg.get("temperature", 0.2),
                num_ctx=ollama_cfg.get("num_ctx"),
                top_p=ollama_cfg.get("top_p"),
                repeat_penalty=ollama_cfg.get("repeat_penalty"),
                client_kwargs=client_kwargs,
            )
            chat_log.write("[green]Connected to local Ollama model.[/green]\n\n")
        except ConfigError as exc:
            self._llm_error = f"Config error: {exc}"
            chat_log.write(f"[bold red]Error:[/bold red] {self._llm_error}\n\n")
        except Exception as exc:
            self._llm_error = f"Failed to initialize Ollama client: {exc}"
            chat_log.write(f"[bold red]Error:[/bold red] {self._llm_error}\n\n")

    def reload_llm_config(self) -> None:
        """Reload LLM settings from llm_config.json and reinitialize the client."""
        chat_log = self.query_one("#chat-messages", RichLog)
        chat_log.write("[dim]Reloading LLM configuration...[/dim]\n")
        self._initialize_llm()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "send-button":
            self._send_message()
        elif event.button.id == "clear-button":
            self._clear_chat()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Send message when Enter is pressed in the input field."""
        if event.input.id == "message-input":
            self._send_message()

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

        if self._llm is None:
            reason = self._llm_error or "LLM client is not initialized."
            chat_log.write(f"[bold red]Assistant:[/bold red] [dim]{reason}[/dim]\n\n")
            input_widget.focus()
            return

        self._set_chat_busy(True)
        chat_log.write("[bold green]Assistant:[/bold green] [dim]Thinking...[/dim]\n")
        self._invoke_llm_worker(message)

        # Focus back to input
        input_widget.focus()

    @work(thread=True)
    def _invoke_llm_worker(self, message: str) -> None:
        """Run Ollama call in a background thread to keep the UI responsive."""
        try:
            response = self._llm.invoke(message)
            content = getattr(response, "content", response)

            if isinstance(content, list):
                content = "".join(str(part) for part in content)
            assistant_text = str(content).strip() or "(No response)"
            self.app.call_from_thread(self._on_llm_result, assistant_text, None)
        except Exception as exc:
            self.app.call_from_thread(self._on_llm_result, None, str(exc))

    def _on_llm_result(self, assistant_text: str | None, error: str | None) -> None:
        """Render worker result in the chat log and re-enable input controls."""
        chat_log = self.query_one("#chat-messages", RichLog)

        if error:
            chat_log.write(
                "[bold red]Assistant:[/bold red] "
                f"[dim]Ollama request failed: {error}[/dim]\n\n"
            )
        else:
            chat_log.write(f"[bold green]Assistant:[/bold green] {assistant_text}\n\n")

        self._set_chat_busy(False)
        self.query_one("#message-input", Input).focus()

    def _set_chat_busy(self, busy: bool) -> None:
        """Disable input controls while the assistant is generating."""
        self.query_one("#message-input", Input).disabled = busy
        self.query_one("#send-button", Button).disabled = busy
        self.query_one("#clear-button", Button).disabled = busy

    def _clear_chat(self) -> None:
        """Clear all chat messages."""
        chat_log = self.query_one("#chat-messages", RichLog)
        chat_log.clear()
        chat_log.write("[bold cyan]LLM Chat Assistant[/bold cyan]\n")
        chat_log.write("[dim]Conversation cleared[/dim]\n\n")
        self.query_one("#message-input", Input).focus()

