#!/usr/bin/env python3
"""
Automated PyInstaller build script for Textual TUI applications.
Collects all dynamic imports from 'textual.widgets' and other known
problematic packages.
"""

import sys
import os
from typing import List
from PyInstaller.__main__ import run as pyinstaller_run
from PyInstaller.utils.hooks import collect_submodules


def get_dynamic_hiddenimports() -> List[str]:
    """Return a list of hidden imports for dynamic packages."""
    hidden: List[str] = []

    # Textual: all widgets submodules (includes _tab, _tabs, etc.)
    try:
        # collect_submodules returns List[str]
        hidden.extend(collect_submodules("textual.widgets"))
    except (ImportError, ModuleNotFoundError) as e:
        print(f"Warning: Could not collect textual.widgets submodules: {e}")
    except Exception as e:  # unexpected error, but still catch
        print(f"Unexpected error collecting textual.widgets: {e}")

    # Also include textual.containers (may be dynamically used)
    try:
        hidden.extend(collect_submodules("textual.containers"))
    except (ImportError, ModuleNotFoundError) as e:
        print(f"Warning: Could not collect textual.containers submodules: {e}")
    except Exception as e:
        print(f"Unexpected error collecting textual.containers: {e}")

    # Add any other packages known to use dynamic imports
    for pkg in ("prompt_toolkit", "rich"):
        try:
            hidden.extend(collect_submodules(pkg))
        except (ImportError, ModuleNotFoundError):
            pass  # optional dependency not installed
        except Exception as e:
            print(f"Warning: Error collecting {pkg}: {e}")

    return hidden


def build(entry_script: str) -> None:
    """Build executable using PyInstaller with dynamic hidden imports."""
    if not os.path.isfile(entry_script):
        print(f"Error: Entry script '{entry_script}' not found.", file=sys.stderr)
        sys.exit(1)

    hidden_imports = get_dynamic_hiddenimports()
    print(f"Collected {len(hidden_imports)} dynamic hidden imports.")
    if hidden_imports:
        print("Sample:", hidden_imports[:5])

    # Prepare PyInstaller arguments (all must be strings)
    base_name = os.path.splitext(entry_script)[0]
    args: List[str] = [
        entry_script,
        "--name",
        base_name,
        "--onefile",
        "--console",
        "--clean",
        "--noconfirm",
    ]

    # Add each hidden import as a separate --hidden-import argument
    for imp in hidden_imports:
        # Ensure imp is a string (it should be, but we cast to be safe)
        args.extend(["--hidden-import", str(imp)])

    # Optional: add data files if needed (example)
    # args.extend(['--add-data', 'path/to/css:css'])

    print("\nRunning PyInstaller with arguments:")
    print(" ".join(args), "\n")
    pyinstaller_run(args)


if __name__ == "__main__":
    # Use command line argument or default to 'run_TUI.py'
    target = sys.argv[1] if len(sys.argv) > 1 else "run_TUI.py"
    build(target)
