from __future__ import annotations

import os


def write_markdown(path: str, content: str, encoding: str = "utf-8") -> None:
    """Write `content` to `path` creating parent directories as needed."""
    path = os.path.expanduser(path)
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding=encoding) as fh:
        fh.write(content)
