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
from urllib import error, parse, request


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


def _resolve_config_path_for_write(config_path: str | Path | None = None) -> Path:
    """Resolve config output path, preferring an existing runtime candidate."""
    if config_path:
        return Path(config_path)
    candidates = default_config_candidates()
    return next(
        (candidate for candidate in candidates if candidate.exists()), candidates[0]
    )


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
        path = next(
            (candidate for candidate in candidates if candidate.exists()), candidates[0]
        )

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


def save_llm_config(
    raw_config: Dict[str, Any], config_path: str | Path | None = None
) -> Path:
    """Validate and save LLM configuration to JSON file."""
    if not isinstance(raw_config, dict):
        raise ConfigError("Config root must be a JSON object.")

    provider = str(raw_config.get("provider", "")).strip().lower()
    if provider != "ollama":
        raise ConfigError("Only provider='ollama' is supported right now.")

    ollama_cfg = raw_config.get("ollama")
    if not isinstance(ollama_cfg, dict):
        raise ConfigError("Config must contain object 'ollama'.")
    if not str(ollama_cfg.get("model", "")).strip():
        raise ConfigError("Config 'ollama.model' is required.")

    path = _resolve_config_path_for_write(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw_config, indent=2) + "\n", encoding="utf-8")
    return path


def test_ollama_connection(
    base_url: str, model: str, timeout_seconds: int = 10
) -> tuple[bool, str]:
    """Test local Ollama reachability and whether model exists in /api/tags."""
    normalized_url = str(base_url).strip().rstrip("/")
    model_name = str(model).strip()
    if not normalized_url:
        return False, "Base URL is required."
    if not model_name:
        return False, "Model name is required."

    tags_url = parse.urljoin(normalized_url + "/", "api/tags")
    try:
        with request.urlopen(tags_url, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except error.URLError as exc:
        return False, f"Cannot connect to Ollama at {normalized_url}: {exc}"
    except Exception as exc:
        return False, f"Failed reading Ollama tags response: {exc}"

    models = payload.get("models", []) if isinstance(payload, dict) else []
    model_names = {
        str(item.get("name", "")).strip() for item in models if isinstance(item, dict)
    }
    if not model_names:
        return (
            True,
            f"Connected to Ollama at {normalized_url}, but no models are installed.",
        )

    # Accept exact match or a tag mismatch like "model" vs "model:latest".
    if model_name in model_names or any(
        name.split(":", 1)[0] == model_name.split(":", 1)[0] for name in model_names
    ):
        return True, f"Connected to Ollama and found model '{model_name}'."

    preview = ", ".join(sorted(model_names)[:8])
    return (
        False,
        f"Connected to Ollama, but model '{model_name}' is missing. Available: {preview}",
    )
