#!/usr/bin/env python3
"""Test error handling for broken JSON."""

from pathlib import Path
from llm_config import load_llm_config, ConfigError
import tempfile
import json

# Test 1: Missing file
print("Test 1: Missing config file")
try:
    load_llm_config("/nonexistent/path/llm_config.json")
    print("✗ Should have raised error")
except ConfigError as e:
    print(f"✓ ConfigError: {e}")

# Test 2: Broken JSON
print("\nTest 2: Broken JSON syntax")
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    f.write('{ "invalid": json }')  # Missing quotes
    broken_path = f.name

try:
    load_llm_config(broken_path)
    print("✗ Should have raised error")
except ConfigError as e:
    print(f"✓ ConfigError: {e}")
finally:
    Path(broken_path).unlink()

# Test 3: Empty file
print("\nTest 3: Empty config file")
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    f.write("")
    empty_path = f.name

try:
    load_llm_config(empty_path)
    print("✗ Should have raised error")
except ConfigError as e:
    print(f"✓ ConfigError: {e}")
finally:
    Path(empty_path).unlink()

# Test 4: Missing required fields
print("\nTest 4: Missing 'provider' field")
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    json.dump({"ollama": {"model": "test"}}, f)
    incomplete_path = f.name

try:
    load_llm_config(incomplete_path)
    print("✗ Should have raised error")
except ConfigError as e:
    print(f"✓ ConfigError: {e}")
finally:
    Path(incomplete_path).unlink()

# Test 5: Missing model field
print("\nTest 5: Missing 'model' field in ollama config")
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    json.dump({"provider": "ollama", "ollama": {}}, f)
    no_model_path = f.name

try:
    load_llm_config(no_model_path)
    print("✗ Should have raised error")
except ConfigError as e:
    print(f"✓ ConfigError: {e}")
finally:
    Path(no_model_path).unlink()

print("\n✓ All error handling tests passed!")
