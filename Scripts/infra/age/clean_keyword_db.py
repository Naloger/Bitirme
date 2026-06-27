# -*- coding: utf-8 -*-
"""Script to clean/reset the keyword graph database context in Apache AGE."""

import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure stdout to use UTF-8 to support Windows console output
if sys.stdout.encoding != 'utf-8':
    reconfigure_stdout = getattr(sys.stdout, 'reconfigure', None)
    if reconfigure_stdout:
        try:
            reconfigure_stdout(encoding='utf-8')
        except Exception:
            pass

PG_HOST = "127.0.0.1"
PG_PORT = "5435"
PG_DB = "keyword_db"
PG_USER = "postgres"
PG_PASSWORD = "local_rag_secret_key_123"
GRAPH_NAME = "keyword_graph"


def main():
    print(f"🧹 Resetting database '{PG_DB}' (graph: '{GRAPH_NAME}')...")
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with conn.cursor() as cursor:
            # Load age and set path
            cursor.execute("LOAD 'age';")
            cursor.execute("SET search_path = ag_catalog, '$user', public;")
            
            # Drop graph
            print(f"   🗑️ Dropping graph '{GRAPH_NAME}'...")
            try:
                cursor.execute(f"SELECT drop_graph('{GRAPH_NAME}', true);")
            except Exception as e:
                print(f"   ℹ️ Note dropping graph: {e}")
                
            # Re-create graph
            print(f"   🛠️ Recreating graph '{GRAPH_NAME}'...")
            cursor.execute(f"SELECT create_graph('{GRAPH_NAME}');")
            
            print(f"✅ Database '{PG_DB}' cleaned and reset successfully.")
        conn.close()
    except Exception as e:
        print(f"❌ Error resetting database '{PG_DB}': {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
