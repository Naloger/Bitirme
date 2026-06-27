# -*- coding: utf-8 -*-
"""Tests for Apache AGE Keyword Graph Database pushes."""

import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import pytest

from Scripts.infra.age.age_helpers import get_age_connection, parse_agtype
from Scripts.infra.age.transpile_keyword import transpile_ppmi_to_age

def safe_print(text: str):
    """Safely prints strings containing emojis without crashing on Windows console."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or 'utf-8'
        print(text.encode(encoding, errors='replace').decode(encoding))


def run_infra_start_script():
    """Executes Scripts/infra/start_infra.py via subprocess to ensure container stack is up."""
    project_root = Path(__file__).resolve().parent.parent
    script_path = project_root / "Scripts" / "infra" / "start_infra.py"
    
    safe_print(f"\n[INFO] Booting infrastructure stack using: {script_path}...")
    res = subprocess.run(
        [sys.executable, str(script_path)]
    )
    
    if res.returncode != 0:
        safe_print(f"[WARN] start_infra.py returned exit code {res.returncode}.")
    else:
        safe_print("[SUCCESS] start_infra.py executed successfully.")



@pytest.fixture(scope="session", autouse=True)
def setup_infrastructure():
    """Ensure docker/podman infrastructure is running before tests."""
    run_infra_start_script()
    print("[INFO] Waiting for PostgreSQL/Apache AGE service to initialize...")
    time.sleep(3)


def test_keyword_db_transpilation_push():
    """
    Test transpilation of PPMI vocabulary and weights from a temporary SQLite
    database directly to the main Apache AGE keyword_db.
    """
    # 1. Create a temporary SQLite database representing lemma_matrix.db
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # Populate the mock SQLite DB with vocabulary and ppmi weights
        sqlite_conn = sqlite3.connect(tmp_path)
        try:
            sqlite_cur = sqlite_conn.cursor()
            sqlite_cur.execute("""
                CREATE TABLE vocabulary (
                    id INTEGER PRIMARY KEY,
                    word TEXT UNIQUE NOT NULL
                );
            """)
            sqlite_cur.execute("""
                CREATE TABLE ppmi_lemma_matrix (
                    id INTEGER PRIMARY KEY,
                    vocab1_id INTEGER NOT NULL,
                    vocab2_id INTEGER NOT NULL,
                    weight REAL NOT NULL
                );
            """)
            
            # Insert mock vocabulary
            vocab_data = [
                (1, "nlp"),
                (2, "transformers"),
                (3, "attention"),
                (4, "mechanism")
            ]
            sqlite_cur.executemany("INSERT INTO vocabulary (id, word) VALUES (?, ?);", vocab_data)
            
            # Insert mock PPMI weights
            ppmi_data = [
                (1, 1, 2, 3.1),  # nlp -> transformers
                (2, 3, 4, 2.2),  # attention -> mechanism
                (3, 2, 3, 1.5)   # transformers -> attention
            ]
            sqlite_cur.executemany("INSERT INTO ppmi_lemma_matrix (id, vocab1_id, vocab2_id, weight) VALUES (?, ?, ?, ?);", ppmi_data)
            sqlite_conn.commit()
        finally:
            sqlite_conn.close()

        # 2. Run the transpiler onto the main keyword_db / keyword_graph
        transpile_ppmi_to_age(
            sqlite_db_path=str(tmp_path),
            pg_db_name="keyword_db",
            graph_name="keyword_graph"
        )

        # 3. Connect to AGE and assert nodes/edges are created properly
        conn = get_age_connection("keyword_db")
        try:
            with conn.cursor() as cur:
                # Query node count
                cur.execute("""
                    SELECT * FROM cypher('keyword_graph', $$
                        MATCH (k:Keyword)
                        RETURN count(k)
                    $$) as (cnt agtype);
                """)
                row = cur.fetchone()
                assert row is not None
                node_count = parse_agtype(row[0])
                assert int(node_count) == 4

                # Query relationships and their weights
                cur.execute("""
                    SELECT * FROM cypher('keyword_graph', $$
                        MATCH (a:Keyword)-[r:CO_OCCUR_WITH]->(b:Keyword)
                        RETURN a.word, b.word, r.weight
                    $$) as (w1 agtype, w2 agtype, wt agtype);
                """)
                edges = cur.fetchall()
                assert len(edges) == 3
                
                # Check specific edge
                edge_map = {}
                for edge in edges:
                    w1 = parse_agtype(edge[0])
                    w2 = parse_agtype(edge[1])
                    wt = parse_agtype(edge[2])
                    edge_map[(w1, w2)] = float(wt)
                
                assert edge_map.get(("nlp", "transformers")) == 3.1
                assert edge_map.get(("attention", "mechanism")) == 2.2
                assert edge_map.get(("transformers", "attention")) == 1.5
                
        finally:
            conn.close()

    finally:
        # Cleanup temporary database file
        if tmp_path.exists():
            tmp_path.unlink()
