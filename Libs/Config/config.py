import json
from pathlib import Path

CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "config.json"

with open(CONFIG_FILE) as f:
    _config = json.load(f)

DATABASE_PATH = (CONFIG_DIR / _config["database"]["path"]).resolve()
