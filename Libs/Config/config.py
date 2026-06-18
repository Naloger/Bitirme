import json
from pathlib import Path

CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "config.json"

with open(CONFIG_FILE) as f:
    _config = json.load(f)

PAGE_DATABASE_PATH = (CONFIG_DIR / _config["database_page"]["path"]).resolve()
LEMMA_DATABASE_PATH = (CONFIG_DIR / _config["database_lemma"]["path"]).resolve()
LEMMA_MATRIX_DATABASE_PATH = (CONFIG_DIR / _config["database_lemma_matrix"]["path"]).resolve()
