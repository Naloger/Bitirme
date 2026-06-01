import json
from pathlib import Path

# Path to the JSON configuration file
_config_path = Path(__file__).with_name("config.json")

# Load and parse JSON
try:
    with open(_config_path, "r", encoding="utf-8") as _f:
        _data = json.load(_f)
except (FileNotFoundError, json.JSONDecodeError, OSError):
        _data = {}

_llm = _data.get("llm_config", {})

# Expose config values as module-level variables
PROVIDER = str(_llm.get("provider", ""))
MODEL = str(_llm.get("model", ""))
API_KEY = _llm.get("api_key")
BASE_URL = _llm.get("base_url")
TEMPERATURE = float(_llm.get("temperature", 0.7) or 0.7)
MAX_TOKENS = int(_llm.get("max_tokens", 8000) or 8000)
TIMEOUT = float(_llm.get("timeout", 60.0) or 60.0)
MAX_LOOPS = int(_llm.get("max_loops", 3) or 3)
