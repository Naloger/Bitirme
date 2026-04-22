"""TUI is temporarily disabled.

This module is intentionally kept as a no-op entrypoint.
"""
from __future__ import annotations

from typing import List


def main(argv: List[str] | None = None) -> int:
    _ = argv
    print("TUI is temporarily disabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
