# -*- coding: utf-8 -*-
"""Script to clean/reset the memory/RDF quadstore graph database context in Apache AGE."""

import sys
from pathlib import Path

# Add backend directory to Python path if running script directly
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from Config.config import AGE_MEMORY_DB, AGE_RDF_GRAPH
from Scripts.infra.age.age_helpers import get_age_connection, drop_age_graph, create_age_graph


def main():
    print(f"🧹 Resetting database '{AGE_MEMORY_DB}' (graph: '{AGE_RDF_GRAPH}')...")
    try:
        conn = get_age_connection(AGE_MEMORY_DB)
        drop_age_graph(conn, AGE_RDF_GRAPH)
        create_age_graph(conn, AGE_RDF_GRAPH)
        conn.close()
        print(f"✅ Database '{AGE_MEMORY_DB}' cleaned and reset successfully.")
    except Exception as e:
        print(f"❌ Error resetting database '{AGE_MEMORY_DB}': {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
