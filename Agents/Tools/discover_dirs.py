from __future__ import annotations

import os
from typing import List


def discover_dirs(
    base_path: str = ".", max_depth: int = 2, include_files: bool = False
) -> List[str]:
    """Discover directories (and optionally files) starting from base_path.

    Returns a list of paths relative to base_path.
    """
    base_path = os.path.expanduser(base_path)
    base_path = os.path.abspath(base_path)
    results: List[str] = []

    def _walk(current: str, depth: int):
        if depth < 0:
            return
        try:
            with os.scandir(current) as it:
                for entry in it:
                    rel = os.path.relpath(entry.path, base_path)
                    if entry.is_dir(follow_symlinks=False):
                        results.append(rel)
                        _walk(entry.path, depth - 1)
                    elif include_files and entry.is_file(follow_symlinks=False):
                        results.append(rel)
        except PermissionError:
            pass

    _walk(base_path, max_depth)
    return results
