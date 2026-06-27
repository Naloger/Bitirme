# -*- coding: utf-8 -*-
"""Script to clean/reset the keyword graph database context in Apache AGE."""

import sys
from pathlib import Path

# Add backend directory to Python path if running script directly
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from Libs.Config.config import AGE_KEYWORD_DB, AGE_KEYWORD_GRAPH
from Scripts.infra.age.age_helpers import get_age_connection, drop_age_graph, create_age_graph


def main():
    print(f"🧹 Resetting database '{AGE_KEYWORD_DB}' (graph: '{AGE_KEYWORD_GRAPH}')...")
    try:
        conn = get_age_connection(AGE_KEYWORD_DB)
        drop_age_graph(conn, AGE_KEYWORD_GRAPH)
        create_age_graph(conn, AGE_KEYWORD_GRAPH)
        conn.close()
        print(f"✅ Database '{AGE_KEYWORD_DB}' cleaned and reset successfully.")
    except Exception as e:
        print(f"❌ Error resetting database '{AGE_KEYWORD_DB}': {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
