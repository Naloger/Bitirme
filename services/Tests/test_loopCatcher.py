# -*- coding: utf-8 -*-
"""Basic I/O tests for loopCatcher module."""
import sys
from pathlib import Path
import json

# Add the inner services package root to path so direct script execution works.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.Config import config
from services.Tests.test_helpers import trace_call


# Import config module using absolute import. Tests add the package root to
# sys.path above, so top-level package imports work reliably during pytest
# collection.

def test_config_loading():
    """Test that config variables have been loaded correctly."""
    assert config.PROVIDER is not None
    assert config.MODEL is not None
    print("✓ test_config_loading passed")


def test_config_has_required_fields():
    """Test that config has required fields."""
    # The `config` module exposes uppercase constants (e.g. PROVIDER,
    # MODEL, BASE_URL, MAX_LOOPS). Ensure these are present.
    assert hasattr(config, 'PROVIDER')
    assert hasattr(config, 'MODEL')
    assert hasattr(config, 'BASE_URL')
    assert hasattr(config, 'MAX_LOOPS')
    print("✓ test_config_has_required_fields passed")


def test_provider_is_valid():
    """Test that provider is one of supported types."""
    provider = config.PROVIDER.lower()
    assert provider in ["ollama", "openai", "deepseek"]
    print("✓ test_provider_is_valid passed")


def test_model_is_configured():
    """Test that model is configured."""
    model = config.MODEL
    assert model is not None
    assert model.strip() != ""
    print("✓ test_model_is_configured passed")


def test_max_loops_is_positive():
    """Test that max_loops is positive."""
    assert config.MAX_LOOPS > 0
    print("✓ test_max_loops_is_positive passed")


def test_base_url_is_valid():
    """Test that base_url is configured."""
    base_url = config.BASE_URL
    assert base_url is not None
    base_url_stripped = base_url.strip()
    assert base_url_stripped != ""
    assert base_url_stripped.startswith("http")
    print("✓ test_base_url_is_valid passed")


def test_config_temperature_in_range():
    """Test that temperature is in valid range."""
    temp = config.TEMPERATURE
    assert 0.0 <= temp <= 2.0
    print("✓ test_config_temperature_in_range passed")


def test_config_max_tokens_positive():
    """Test that max_tokens is positive."""
    assert config.MAX_TOKENS > 0
    print("✓ test_config_max_tokens_positive passed")


def test_loop_safe_response_structure():
    """Test LoopSafeResponse structure."""
    from services.AgentMiddlewares.LoopCatcherMiddleware.loopCatcher import LoopSafeResponse

    response = trace_call(LoopSafeResponse, conclusion="Test conclusion")
    assert response.conclusion == "Test conclusion"
    assert isinstance(response, LoopSafeResponse)
    print("✓ test_loop_safe_response_structure passed")


def test_loop_safe_response_validation():
    """Test LoopSafeResponse validation."""
    from services.AgentMiddlewares.LoopCatcherMiddleware.loopCatcher import LoopSafeResponse

    
    # Valid response
    response = trace_call(LoopSafeResponse, conclusion="This is a valid conclusion.")
    assert response.conclusion == "This is a valid conclusion."
    print("✓ test_loop_safe_response_validation passed")


def test_config_json_structure():
    """Test that config JSON has correct structure."""
    services_subdir = Path(__file__).resolve().parent.parent
    config_path = services_subdir / "Config" / "config.json"

    with open(config_path, 'r', encoding='utf-8') as f:
        config_dict = json.load(f)
    
    # Configuration JSON uses the "llm_config" key in this project.
    assert "llm_config" in config_dict
    api_config = config_dict["llm_config"]
    required_keys = ["provider", "model", "base_url", "max_loops"]
    for key in required_keys:
        assert key in api_config
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
