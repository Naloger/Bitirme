import json
from pathlib import Path

# Path to the JSON configuration file
_config_path = Path(__file__).with_name("config.json")

# Load and parse JSON
try:
    with open(_config_path, "r", encoding="utf-8") as _f:
        _data = json.load(_f)
except Exception:
        _data = {}

_llm = _data.get("llm_config", {})

# Expose config values as module-level variables
PROVIDER = str(_llm.get("provider", ""))
MODEL = str(_llm.get("model", ""))
API_KEY = _llm.get("api_key")
BASE_URL = _llm.get("base_url")
TEMPERATURE = float(_llm.get("temperature"))
MAX_TOKENS = int(_llm.get("max_tokens"))
TIMEOUT = float(_llm.get("timeout"))
MAX_LOOPS = int(_llm.get("max_loops"))
