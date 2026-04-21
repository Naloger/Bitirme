"""Shared LLM configuration helpers.

Currently supports only Ollama provider, but keeps a provider field so
additional backends can be added without changing node interfaces.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG = {
    "provider": "ollama",
    "ollama": {
        "base_url": "http://127.0.0.1:11434",
        "model": "qwen3:8b",
        "temperature": 0.2,
        "num_ctx": 4096,
        "timeout_seconds": 120,
    },
    "loop_guard": {
        "max_loops": 2,
        "max_repeated_chunk": 5,
        "repetition_window": 24,
        "thinking_feedback_chars": 1200,
    },
}


@dataclass
class LLMConfig:
    provider: str
    raw: Dict[str, Any]


class ConfigError(ValueError):
    """Raised when config file content is invalid."""


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_config_path() -> Path:
    return project_root() / "llm_config.json"


def _deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_llm_config(config_path: str | Path | None = None) -> LLMConfig:
    path = Path(config_path) if config_path else default_config_path()
    data = dict(DEFAULT_CONFIG)

    if path.exists():
        text = path.read_text(encoding="utf-8")
        user_config = json.loads(text) if text.strip() else {}
        if not isinstance(user_config, dict):
            raise ConfigError("Config root must be a JSON object.")
        data = _deep_merge(DEFAULT_CONFIG, user_config)

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

