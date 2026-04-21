"""Thin entrypoint: delegate execution to the TUI runner."""
from __future__ import annotations

from TUI.tui_app import main as tui_main


if __name__ == "__main__":
    raise SystemExit(tui_main())
