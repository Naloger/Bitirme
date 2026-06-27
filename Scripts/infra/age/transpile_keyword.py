# -*- coding: utf-8 -*-
"""Script to transpile keyword co-occurrences from SQLite to Apache AGE."""

import json
import sqlite3
import sys
from pathlib import Path

# Add backend directory to Python path if running script directly
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from Libs.Config.config import LEMMA_MATRIX_DATABASE_PATH, AGE_KEYWORD_DB, AGE_KEYWORD_GRAPH
from Scripts.infra.age.age_helpers import (
    ensure_database_exists,
    get_age_connection,
    drop_age_graph,
    create_age_graph,
    execute_cypher_param
)


def transpile_ppmi_to_age(sqlite_db_path: str, pg_db_name: str = AGE_KEYWORD_DB, graph_name: str = AGE_KEYWORD_GRAPH) -> None:
    """
    Read vocabulary and ppmi_lemma_matrix from SQLite database and transpile
    them to a node-weight-node keyword graph in Apache AGE.
    """
    print(f"\n🚀 Starting transpilation from SQLite: {sqlite_db_path} to AGE DB: {pg_db_name} (Graph: {graph_name})...")
    
    # 1. Ensure PG Database exists
    ensure_database_exists(pg_db_name)
    
    # 2. Read SQLite data
    print(f"[INFO] Reading data from SQLite '{sqlite_db_path}'...")
    sqlite_conn = sqlite3.connect(sqlite_db_path)
    sqlite_conn.row_factory = sqlite3.Row
    try:
        sqlite_cur = sqlite_conn.cursor()
        
        # Read vocabulary
        sqlite_cur.execute("SELECT id, word FROM vocabulary;")
        vocab_rows = sqlite_cur.fetchall()
        vocab_list = [{"id": r["id"], "word": r["word"]} for r in vocab_rows]
        print(f"   Loaded {len(vocab_list)} vocabulary words from SQLite.")
        
        # Read PPMI matrix weights
        sqlite_cur.execute("SELECT vocab1_id, vocab2_id, weight FROM ppmi_lemma_matrix;")
        ppmi_rows = sqlite_cur.fetchall()
        ppmi_list = [
            {"v1_id": r["vocab1_id"], "v2_id": r["vocab2_id"], "weight": float(r["weight"])}
            for r in ppmi_rows
        ]
        print(f"   Loaded {len(ppmi_list)} PPMI weight links from SQLite.")
    except Exception as e:
        print(f"❌ Error reading SQLite database: {e}")
        sqlite_conn.close()
        raise
    finally:
        sqlite_conn.close()

    # 3. Connect to AGE and reset the graph
    pg_conn = get_age_connection(pg_db_name)
    try:
        # DDL operations must run in autocommit mode
        pg_conn.autocommit = True
        drop_age_graph(pg_conn, graph_name)
        create_age_graph(pg_conn, graph_name)
        
        # Turn OFF autocommit to run all bulk insertions in a single transaction
        pg_conn.autocommit = False
        
        # 4. Insert vocabulary nodes in batches
        print(f"[INFO] Inserting {len(vocab_list)} Keyword nodes into graph '{graph_name}'...")
        batch_size = 2000
        with pg_conn.cursor() as cur:
            for i in range(0, len(vocab_list), batch_size):
                batch = vocab_list[i : i + batch_size]
                execute_cypher_param(
                    cur=cur,
                    graph_name=graph_name,
                    cypher_query="UNWIND $batch AS item CREATE (k:Keyword) SET k.word = item.word, k.sqlite_id = item.id",
                    params_dict={"batch": batch}
                )
            print("   ✅ Keyword nodes inserted.")
            
            # 5. Insert co-occurrence edges in batches
            print(f"[INFO] Inserting {len(ppmi_list)} CO_OCCUR_WITH edges into graph '{graph_name}'...")
            for i in range(0, len(ppmi_list), batch_size):
                batch = ppmi_list[i : i + batch_size]
                execute_cypher_param(
                    cur=cur,
                    graph_name=graph_name,
                    cypher_query=(
                        "UNWIND $batch AS edge "
                        "MATCH (a:Keyword) WHERE a.sqlite_id = edge.v1_id "
                        "MATCH (b:Keyword) WHERE b.sqlite_id = edge.v2_id "
                        "CREATE (a)-[:CO_OCCUR_WITH {weight: edge.weight}]->(b)"
                    ),
                    params_dict={"batch": batch}
                )
            print("   ✅ CO_OCCUR_WITH edges inserted.")
            
        # Commit the transaction holding all bulk inserts
        pg_conn.commit()
        print(f"🎉 Transpilation complete! Database '{pg_db_name}' now holds the keyword graph.")
    except Exception as e:
        pg_conn.rollback()
        print(f"❌ Error during transpilation: {e}")
        raise
    finally:
        pg_conn.close()



if __name__ == "__main__":
    # If run directly, transpile the default lemma matrix database to the main keyword_db
    print(f"[INFO] Resolving default SQLite DB path: {LEMMA_MATRIX_DATABASE_PATH}")
    if not Path(LEMMA_MATRIX_DATABASE_PATH).exists():
        print(f"❌ Default SQLite database does not exist at: {LEMMA_MATRIX_DATABASE_PATH}")
        sys.exit(1)
        
    transpile_ppmi_to_age(
        sqlite_db_path=str(LEMMA_MATRIX_DATABASE_PATH),
        pg_db_name=AGE_KEYWORD_DB,
        graph_name=AGE_KEYWORD_GRAPH
    )
