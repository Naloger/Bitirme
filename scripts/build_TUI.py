"""
Automated PyInstaller build script for Textual TUI applications.
Collects all dynamic imports from 'textual.widgets' and other known
problematic packages.

Edit the TUI_ENTRY_PATH variable below to point to your TUI script.
"""

import sys
import os
import shutil
from pathlib import Path
from typing import List
from PyInstaller.__main__ import run as pyinstaller_run
from PyInstaller.utils.hooks import collect_submodules

# ============================================================
# SET YOUR TUI ENTRY SCRIPT HERE (relative or absolute path)

BASE = Path(__file__).parents[1]
TUI_ENTRY_PATH = BASE / "run_TUI.py"

# ============================================================


def get_dynamic_hiddenimports() -> List[str]:
    """Return a list of hidden imports for dynamic packages."""
    hidden: List[str] = []

    # Textual: all widgets submodules (includes _tab, _tabs, etc.)
    try:
        hidden.extend(collect_submodules("textual.widgets"))
    except (ImportError, ModuleNotFoundError) as e:
        print(f"Warning: Could not collect textual.widgets submodules: {e}")
    except Exception as e:
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
            pass
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

    # ✅ Extract just the base name (e.g., "run_TUI" from "/path/to/run_TUI.py")
    base_name = os.path.splitext(os.path.basename(entry_script))[0]

    args: List[str] = [
        entry_script,
        "--name",
        base_name,
        "--onefile",
        "--console",
        "--clean",
        "--noconfirm",
        "--distpath",
        str(BASE / "build" / "dist"),
        "--workpath",
        str(BASE / "build" / "temp"),
        "--specpath",
        str(BASE / "build"),
    ]

    for imp in hidden_imports:
        args.extend(["--hidden-import", str(imp)])

    print("\nRunning PyInstaller with arguments:")
    print(" ".join(args), "\n")
    pyinstaller_run(args)

    config_src = BASE / "llm_config.json"
    config_dst = BASE / "build" / "dist" / "llm_config.json"
    if config_src.exists():
        try:
            shutil.copy2(config_src, config_dst)
            print(f"Copied config to {config_dst}")
        except Exception as e:
            print(f"Warning: could not copy llm_config.json to dist folder: {e}")
    else:
        print(f"Warning: llm_config.json not found at {config_src}; EXE will use runtime fallback only.")


if __name__ == "__main__":
    # Convert Path to string before passing to build()
    build(str(TUI_ENTRY_PATH))
