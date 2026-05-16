# -*- coding: utf-8 -*-
"""Basic I/O tests for loopCatcher module."""
import sys
from pathlib import Path

# Add services directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import os

try:
    from ..Config.config import AppConfig
except ImportError:
    from Config.config import AppConfig


def setup_config():
    """Setup config path for tests."""
    # Get the absolute path to config.json
    test_dir = os.path.dirname(os.path.abspath(__file__))
    services_subdir = os.path.dirname(test_dir)
    config_path = os.path.join(services_subdir, "Config", "config.json")
    return config_path


def test_config_loading():
    """Test that config can be loaded from JSON file."""
    config_path = setup_config()
    if not os.path.exists(config_path):
        raise AssertionError(f"Config file not found at {config_path}")
    config = AppConfig.from_json_file(config_path)
    if config is None:
        raise AssertionError("Config is None")
    if config.api_config is None:
        raise AssertionError("api_config is None")
    print("✓ test_config_loading passed")


def test_config_has_required_fields():
    """Test that config has required fields."""
    config_path = setup_config()
    config = AppConfig.from_json_file(config_path)
    api = config.api_config
    if not hasattr(api, 'provider'):
        raise AssertionError("Missing 'provider' attribute")
    if not hasattr(api, 'model'):
        raise AssertionError("Missing 'model' attribute")
    if not hasattr(api, 'base_url'):
        raise AssertionError("Missing 'base_url' attribute")
    if not hasattr(api, 'max_loops'):
        raise AssertionError("Missing 'max_loops' attribute")
    print("✓ test_config_has_required_fields passed")


def test_provider_is_valid():
    """Test that provider is one of supported types."""
    config_path = setup_config()
    config = AppConfig.from_json_file(config_path)
    provider = config.api_config.provider.lower()
    if provider not in ["ollama", "openai", "deepseek"]:
        raise AssertionError(f"Invalid provider: {provider}")
    print("✓ test_provider_is_valid passed")


def test_model_is_configured():
    """Test that model is configured."""
    config_path = setup_config()
    config = AppConfig.from_json_file(config_path)
    model = config.api_config.model
    if model is None:
        raise AssertionError("Model should not be None")
    model_stripped = model.strip()
    if not model_stripped:
        raise AssertionError("Model should not be empty")
    print("✓ test_model_is_configured passed")


def test_max_loops_is_positive():
    """Test that max_loops is positive."""
    config_path = setup_config()
    config = AppConfig.from_json_file(config_path)
    if config.api_config.max_loops <= 0:
        raise AssertionError(f"max_loops should be positive, got {config.api_config.max_loops}")
    print("✓ test_max_loops_is_positive passed")


def test_base_url_is_valid():
    """Test that base_url is configured."""
    config_path = setup_config()
    config = AppConfig.from_json_file(config_path)
    base_url = config.api_config.base_url
    if base_url is None:
        raise AssertionError("Base URL should not be None")
    base_url_stripped = base_url.strip()
    if not base_url_stripped:
        raise AssertionError("Base URL should not be empty")
    if not base_url_stripped.startswith("http"):
        raise AssertionError("Base URL should start with http")
    print("✓ test_base_url_is_valid passed")


def test_config_temperature_in_range():
    """Test that temperature is in valid range."""
    config_path = setup_config()
    config = AppConfig.from_json_file(config_path)
    temp = config.api_config.temperature
    if not (0.0 <= temp <= 2.0):
        raise AssertionError(f"Temperature should be between 0 and 2, got {temp}")
    print("✓ test_config_temperature_in_range passed")


def test_config_max_tokens_positive():
    """Test that max_tokens is positive."""
    config_path = setup_config()
    config = AppConfig.from_json_file(config_path)
    if config.api_config.max_tokens <= 0:
        raise AssertionError(f"max_tokens should be positive, got {config.api_config.max_tokens}")
    print("✓ test_config_max_tokens_positive passed")


def test_loop_safe_response_structure():
    """Test LoopSafeResponse structure."""
    try:
        from ..AgentMiddlewares.LoopCatcherMiddleware.loopCatcher import LoopSafeResponse
    except ImportError:
        from AgentMiddlewares.LoopCatcherMiddleware.loopCatcher import LoopSafeResponse
    
    response = LoopSafeResponse(conclusion="Test conclusion")
    if response.conclusion != "Test conclusion":
        raise AssertionError(f"Expected 'Test conclusion', got {response.conclusion}")
    if not isinstance(response, LoopSafeResponse):
        raise AssertionError(f"Expected LoopSafeResponse instance, got {type(response)}")
    print("✓ test_loop_safe_response_structure passed")


def test_loop_safe_response_validation():
    """Test LoopSafeResponse validation."""
    try:
        from ..AgentMiddlewares.LoopCatcherMiddleware.loopCatcher import LoopSafeResponse
    except ImportError:
        from AgentMiddlewares.LoopCatcherMiddleware.loopCatcher import LoopSafeResponse
    
    # Valid response
    response = LoopSafeResponse(conclusion="This is a valid conclusion.")
    if response.conclusion != "This is a valid conclusion.":
        raise AssertionError(f"Expected 'This is a valid conclusion.', got {response.conclusion}")
    print("✓ test_loop_safe_response_validation passed")


def test_config_json_structure():
    """Test that config JSON has correct structure."""
    config_path = setup_config()
    with open(config_path, 'r', encoding='utf-8') as f:
        config_dict = json.load(f)
    
    if "api_config" not in config_dict:
        raise AssertionError("Missing 'api_config' in config JSON")
    api_config = config_dict["api_config"]
    required_keys = ["provider", "model", "base_url", "max_loops"]
    for key in required_keys:
        if key not in api_config:
            raise AssertionError(f"Missing required key: {key}")
    print("✓ test_config_json_structure passed")


if __name__ == "__main__":
    test_config_loading()
    test_config_has_required_fields()
    test_provider_is_valid()
    test_model_is_configured()
    test_max_loops_is_positive()
    test_base_url_is_valid()
    test_config_temperature_in_range()
    test_config_max_tokens_positive()
    test_loop_safe_response_structure()
    test_loop_safe_response_validation()
    test_config_json_structure()
    print("\n✓ All tests passed!")

# Integration test note:
# To test generate_with_protection with actual model communication:
# 1. Ensure Ollama service is running on http://localhost:11434
# 2. Verify the configured model is available (e.g., granite4.1:3b)
# 3. Run: python test_loopCatcher.py
# 
# Example results:
# - Fail for qwen3.5:0.8b (too small model, prone to loops)
# - Success for granite4.1:3b (larger model with better consistency)
