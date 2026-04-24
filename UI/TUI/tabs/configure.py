"""Configure tab."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from llm_config import (
    ConfigError,
    load_llm_config,
    save_llm_config,
    test_ollama_connection,
)
from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import Button, Input, RichLog, Select, Static

from UI.TUI.tabs.chat_tab import ChatTab


class Configure(VerticalScroll):
    """Configure tab content."""

    _raw_config: dict[str, Any] | None = None
    _ollama_status: str = (
        "unknown"  # "connected", "disconnected", "unknown", "checking"
    )

    DEFAULT_CSS = """
    Configure {
        width: 100%;
        height: 100%;
        background: $panel;
        padding: 1;
        layout: vertical;
        overflow-y: auto;
    }

    Configure #status-bar {
        width: 100%;
        height: auto;
        layout: horizontal;
        border: solid $accent;
        padding: 1;
        margin-bottom: 1;
    }

    Configure #status-label {
        width: auto;
        content-align: left middle;
    }

    Configure #status-indicator {
        width: auto;
        content-align: center middle;
        margin-left: 2;
    }

    Configure #config-form {
        width: 100%;
        height: auto;
        layout: vertical;
        border: solid $accent;
        padding: 1;
        margin-bottom: 1;
    }

    Configure .config-row {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin-bottom: 1;
    }

    Configure .config-label {
        width: 24;
        content-align: left middle;
    }

    Configure .config-input {
        width: 1fr;
    }

    Configure #config-buttons {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin-top: 1;
    }

    Configure #config-buttons Button {
        width: 1fr;
        margin: 0 1;
    }

    Configure #config-log {
        width: 100%;
        height: 1fr;
        border: solid $accent;
        background: $surface;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the configure tab."""
        # Status bar
        with Container(id="status-bar"):
            yield Static("Ollama Status:", id="status-label")
            yield Static("[dim]Checking...[/dim]", id="status-indicator")

        with Container(id="config-form"):
            with Horizontal(classes="config-row"):
                yield Static("Provider", classes="config-label")
                yield Select(
                    options=[("local ollama", "ollama")],
                    value="ollama",
                    id="provider-select",
                    classes="config-input",
                    allow_blank=False,
                )

            with Horizontal(classes="config-row"):
                yield Static("Base URL", classes="config-label")
                yield Input(id="base-url-input", classes="config-input")

            with Horizontal(classes="config-row"):
                yield Static("Model", classes="config-label")
                yield Input(id="model-input", classes="config-input")

            with Horizontal(classes="config-row"):
                yield Static("Temperature", classes="config-label")
                yield Input(id="temperature-input", classes="config-input")

            with Horizontal(classes="config-row"):
                yield Static("Num Ctx", classes="config-label")
                yield Input(id="num-ctx-input", classes="config-input")

            with Horizontal(classes="config-row"):
                yield Static("Timeout (seconds)", classes="config-label")
                yield Input(id="timeout-input", classes="config-input")

            with Horizontal(classes="config-row"):
                yield Static("Top P", classes="config-label")
                yield Input(id="top-p-input", classes="config-input")

            with Horizontal(classes="config-row"):
                yield Static("Repeat Penalty", classes="config-label")
                yield Input(id="repeat-penalty-input", classes="config-input")

            with Horizontal(id="config-buttons"):
                yield Button(
                    "Test Ollama", id="test-connection-button", variant="primary"
                )
                yield Button(
                    "Save and Reload", id="save-config-button", variant="success"
                )
                yield Button(
                    "Reload from File", id="reload-config-button", variant="default"
                )

        yield RichLog(id="config-log", markup=True)

    def on_mount(self) -> None:
        """Initialize the configure tab."""
        config_log = self.query_one("#config-log", RichLog)
        config_log.write("[bold cyan]Configuration Settings[/bold cyan]\n")
        config_log.write(
            "[dim]Edit local Ollama settings and save to llm_config.json[/dim]\n\n"
        )
        self._load_config_into_form()
        self._update_status("Checking Ollama connection...")
        self._check_ollama_status()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle configure actions."""
        if event.button.id == "test-connection-button":
            self._test_connection()
        elif event.button.id == "save-config-button":
            self._save_and_reload()
        elif event.button.id == "reload-config-button":
            self._load_config_into_form()

    def _load_config_into_form(self) -> None:
        """Load current config file into input fields."""
        try:
            config = load_llm_config()
        except ConfigError as exc:
            self._log(f"[bold red]Config load error:[/bold red] {exc}")
            return

        self._raw_config = deepcopy(config.raw)
        ollama_cfg = config.raw.get("ollama", {})

        self.query_one("#provider-select", Select).value = "ollama"
        self.query_one("#base-url-input", Input).value = str(
            ollama_cfg.get("base_url", "")
        )
        self.query_one("#model-input", Input).value = str(ollama_cfg.get("model", ""))
        self.query_one("#temperature-input", Input).value = self._to_text(
            ollama_cfg.get("temperature", 0.2)
        )
        self.query_one("#num-ctx-input", Input).value = self._to_text(
            ollama_cfg.get("num_ctx")
        )
        self.query_one("#timeout-input", Input).value = self._to_text(
            ollama_cfg.get("timeout_seconds", 300)
        )
        self.query_one("#top-p-input", Input).value = self._to_text(
            ollama_cfg.get("top_p")
        )
        self.query_one("#repeat-penalty-input", Input).value = self._to_text(
            ollama_cfg.get("repeat_penalty")
        )
        self._log("[green]Loaded settings from llm_config.json[/green]")

    def _update_status(self, message: str) -> None:
        """Update the status indicator with a message."""
        status_widget = self.query_one("#status-indicator", Static)
        status_widget.update(message)

    @work(thread=True)
    def _check_ollama_status(self) -> None:
        """Check Ollama connection status in background thread."""
        try:
            config = load_llm_config()
            ollama_cfg = config.raw.get("ollama", {})
            base_url = str(ollama_cfg.get("base_url", ""))
            model = str(ollama_cfg.get("model", ""))
            timeout_value = ollama_cfg.get("timeout_seconds", 10)
            timeout_seconds = int(timeout_value) if timeout_value else 10

            ok, message = test_ollama_connection(base_url, model, timeout_seconds)

            if ok:
                self._ollama_status = "connected"
                status_msg = f"[green]✓ Connected[/green] — {message}"
            else:
                self._ollama_status = "disconnected"
                status_msg = f"[bold red]✗ Disconnected[/bold red] — {message}"

            self.app.call_from_thread(self._update_status, status_msg)
            self.app.call_from_thread(self._log, status_msg)
        except ConfigError as exc:
            self._ollama_status = "unknown"
            msg = f"[bold red]Config Error:[/bold red] {exc}"
            self.app.call_from_thread(self._update_status, "[dim]Config Error[/dim]")
            self.app.call_from_thread(self._log, msg)
        except Exception as exc:
            self._ollama_status = "unknown"
            msg = f"[bold red]Status Check Failed:[/bold red] {exc}"
            self.app.call_from_thread(self._update_status, "[dim]Error[/dim]")
            self.app.call_from_thread(self._log, msg)

    @work(thread=True)
    def _test_connection(self) -> None:
        """Test Ollama connection using current form values."""
        try:
            candidate = self._build_candidate_config()
            self._update_status("[dim]Testing connection...[/dim]")
            ollama_cfg = candidate["ollama"]
            timeout_value = ollama_cfg.get("timeout_seconds")
            timeout_seconds = int(timeout_value) if timeout_value is not None else 10
            ok, message = test_ollama_connection(
                base_url=str(ollama_cfg.get("base_url", "")),
                model=str(ollama_cfg.get("model", "")),
                timeout_seconds=timeout_seconds,
            )
            if ok:
                self._ollama_status = "connected"
                self._log(f"[green]✓ Test Passed[/green] — {message}")
                self._update_status("[green]✓ Connected[/green]")
            else:
                self._ollama_status = "disconnected"
                self._log(f"[bold red]✗ Test Failed[/bold red] — {message}")
                self._update_status("[bold red]✗ Disconnected[/bold red]")
        except ConfigError as exc:
            self._log(f"[bold red]Validation Error:[/bold red] {exc}")
            self._update_status("[bold red]Validation Error[/bold red]")

    @work(thread=True)
    def _save_and_reload(self) -> None:
        """Save edited settings and reload active chat LLM client."""
        try:
            candidate = self._build_candidate_config()
            saved_path = save_llm_config(candidate)
            self._raw_config = deepcopy(candidate)
            self._log(f"[green]Saved configuration:[/green] {saved_path}")
            self._reload_chat_tab()
            self._update_status("[green]✓ Config saved[/green]")
            self._check_ollama_status()
        except ConfigError as exc:
            self._log(f"[bold red]Save error:[/bold red] {exc}")
            self._update_status("[bold red]Save error[/bold red]")

    def _reload_chat_tab(self) -> None:
        """Reload ChatTab model client after config changes."""
        try:
            chat_tab = self.app.query_one(ChatTab)
            chat_tab.reload_llm_config()
            self._log("[green]Chat tab reloaded with updated configuration.[/green]")
        except Exception as exc:
            self._log(f"[yellow]Saved, but could not reload chat tab:[/yellow] {exc}")

    def _build_candidate_config(self) -> dict[str, Any]:
        """Build a full config object from form values."""
        provider = self.query_one("#provider-select", Select).value
        if provider != "ollama":
            raise ConfigError("Only 'local ollama' provider is supported.")

        raw = deepcopy(self._raw_config) if isinstance(self._raw_config, dict) else {}
        raw["provider"] = "ollama"

        ollama_cfg: dict[str, Any] = {}
        if isinstance(raw.get("ollama"), dict):
            ollama_cfg = raw["ollama"]

        ollama_cfg["base_url"] = self.query_one("#base-url-input", Input).value.strip()
        ollama_cfg["model"] = self.query_one("#model-input", Input).value.strip()
        ollama_cfg["temperature"] = self._parse_required_float(
            "#temperature-input", "temperature"
        )
        ollama_cfg["num_ctx"] = self._parse_optional_int("#num-ctx-input")
        ollama_cfg["timeout_seconds"] = self._parse_optional_int("#timeout-input")
        ollama_cfg["top_p"] = self._parse_optional_float("#top-p-input")
        ollama_cfg["repeat_penalty"] = self._parse_optional_float(
            "#repeat-penalty-input"
        )

        if not ollama_cfg["base_url"]:
            raise ConfigError("Config 'ollama.base_url' is required.")
        if not ollama_cfg["model"]:
            raise ConfigError("Config 'ollama.model' is required.")

        raw["ollama"] = ollama_cfg
        return raw

    def _parse_required_float(self, input_id: str, field_name: str) -> float:
        text = self.query_one(input_id, Input).value.strip()
        if not text:
            raise ConfigError(f"Config 'ollama.{field_name}' is required.")
        try:
            return float(text)
        except ValueError as exc:
            raise ConfigError(
                f"Config 'ollama.{field_name}' must be a number."
            ) from exc

    def _parse_optional_int(self, input_id: str) -> int | None:
        text = self.query_one(input_id, Input).value.strip()
        if not text or text.lower() == "null":
            return None
        try:
            return int(text)
        except ValueError as exc:
            raise ConfigError(f"Value in {input_id} must be an integer.") from exc

    def _parse_optional_float(self, input_id: str) -> float | None:
        text = self.query_one(input_id, Input).value.strip()
        if not text or text.lower() == "null":
            return None
        try:
            return float(text)
        except ValueError as exc:
            raise ConfigError(f"Value in {input_id} must be a number.") from exc

    @staticmethod
    def _to_text(value: Any) -> str:
        return "" if value is None else str(value)

    def _log(self, message: str) -> None:
        self.query_one("#config-log", RichLog).write(f"{message}\n")
