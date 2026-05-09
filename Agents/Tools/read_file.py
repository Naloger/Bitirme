from __future__ import annotations

import os


def read_file(path: str, encoding: str = "utf-8") -> str:
    """Read and return the contents of a file. Expands ~ and relative paths."""
    path = os.path.expanduser(path)
    with open(path, "r", encoding=encoding) as fh:
        return fh.read()
