#!/usr/bin/env python3
"""Test new llm_config JSON-only loading."""

from llm_config import load_llm_config, ConfigError

try:
    cfg = load_llm_config()
    print("✓ Config loaded successfully")
    print(f"  provider: {cfg.provider}")
    print(f"  model: {cfg.raw['ollama']['model']}")
    print(f"  base_url: {cfg.raw['ollama']['base_url']}")
except ConfigError as e:
    print(f"✗ ConfigError: {e}")
except Exception as e:
    print(f"✗ Error: {e}")
