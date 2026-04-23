"""Shared LLM configuration helpers.

Currently supports only Ollama provider, but keeps a provider field so
additional backends can be added without changing node interfaces.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any, Dict



@dataclass
class LLMConfig:
    provider: str
    raw: Dict[str, Any]


class ConfigError(ValueError):
    """Raised when config file content is invalid."""


def project_root() -> Path:
    return Path(__file__).resolve().parent


def runtime_base_dir() -> Path:
    """Return the base directory for runtime assets.

    In frozen builds (e.g. PyInstaller), module files may live in a temp
    extraction directory. In that case we resolve relative assets from the
    executable directory.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return project_root()


def default_config_candidates() -> list[Path]:
    """Possible config locations in priority order."""
    candidates: list[Path] = [runtime_base_dir() / "llm_config.json"]
    cwd_candidate = Path.cwd() / "llm_config.json"
    if cwd_candidate not in candidates:
        candidates.append(cwd_candidate)
    return candidates


def default_config_path() -> Path:
    return default_config_candidates()[0]


def load_llm_config(config_path: str | Path | None = None) -> LLMConfig:
    """Load LLM configuration from JSON file.

    Args:
        config_path: Optional path to config file. Defaults to llm_config.json in project root.

    Raises:
        ConfigError: If config file is missing, invalid JSON, or missing required fields.
    """
    if config_path:
        path = Path(config_path)
    else:
        candidates = default_config_candidates()
        path = next((candidate for candidate in candidates if candidate.exists()), candidates[0])

    if not path.exists():
        if config_path:
            raise ConfigError(f"Config file not found: {path}")
        checked = ", ".join(str(p) for p in default_config_candidates())
        raise ConfigError(f"Config file not found. Checked: {checked}")

    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ConfigError(f"Config file is empty: {path}")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in config file {path}: {exc}")

    if not isinstance(data, dict):
        raise ConfigError("Config root must be a JSON object.")

    provider = str(data.get("provider", "")).strip().lower()
    if not provider:
        raise ConfigError("Config must define 'provider'.")
    if provider != "ollama":
        raise ConfigError("Only provider='ollama' is supported right now.")

    ollama_cfg = data.get("ollama")
    if not isinstance(ollama_cfg, dict):
        raise ConfigError("Config must contain object 'ollama'.")

    if not ollama_cfg.get("model"):
        raise ConfigError("Config 'ollama.model' is required.")

    return LLMConfig(provider=provider, raw=data)

