# -*- coding: utf-8 -*-
"""Script to bootstrap and initialize PostgreSQL databases and Apache AGE graphs."""

import sys
from pathlib import Path

# Add project root to python path if needed
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from Config.config import (
    AGE_MEMORY_DB,
    AGE_RDF_GRAPH
)
from Scripts.infra.age.age_helpers import (
    ensure_database_exists,
    get_age_connection,
    create_age_graph
)


def main():
    print("🔌 Starting bootstrapping of Apache AGE databases...")
    try:
        # 2. Initialize memory_db & rdf_quadstore_graph
        print(f"\n⚙️ Configuring database: '{AGE_MEMORY_DB}'...")
        ensure_database_exists(AGE_MEMORY_DB)
        conn = get_age_connection(AGE_MEMORY_DB)
        create_age_graph(conn, AGE_RDF_GRAPH)
        conn.close()

        print("\n🎉 Apache AGE database context setup complete!")
    except Exception as e:
        print(f"\n❌ Error setting up databases: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
