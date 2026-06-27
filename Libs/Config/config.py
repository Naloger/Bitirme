import json
from pathlib import Path

CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "config.json"

with open(CONFIG_FILE) as f:
    _config = json.load(f)

PAGE_DATABASE_PATH = (CONFIG_DIR / _config["database_page"]["path"]).resolve()
LEMMA_MATRIX_DATABASE_PATH = (CONFIG_DIR / _config["database_lemma_matrix"]["path"]).resolve()

# Scripts configuration settings
START_API_HOST = _config.get("start_api", {}).get("host", "127.0.0.1")
START_API_PORT = int(_config.get("start_api", {}).get("port", 8090))
START_API_RELOAD = bool(_config.get("start_api", {}).get("reload", True))

BUILD_HIERARCHY_MAX_LEVELS = int(_config.get("build_hierarchy", {}).get("max_levels", 5))

BUILD_PPMI_THRESHOLD = float(_config.get("build_ppmi_table", {}).get("threshold", 0.0))

VISUALIZE_HIERARCHY_FORCE_ASCII = bool(_config.get("visualize_hierarchy", {}).get("force_ascii", False))

# Apache AGE configuration settings
_age_config = _config.get("apache_age", {})
AGE_HOST = _age_config.get("host", "127.0.0.1")
AGE_PORT = int(_age_config.get("port", 5435))
AGE_USER = _age_config.get("user", "postgres")
AGE_PASSWORD = _age_config.get("password", "local_rag_secret_key_123")
AGE_DEFAULT_DB = _age_config.get("default_db", "postgres")
AGE_KEYWORD_DB = _age_config.get("keyword_db", "keyword_db")
AGE_MEMORY_DB = _age_config.get("memory_db", "memory_db")
AGE_KEYWORD_GRAPH = _age_config.get("keyword_graph", "keyword_graph")
AGE_RDF_GRAPH = _age_config.get("rdf_quadstore_graph", "rdf_quadstore_graph")


