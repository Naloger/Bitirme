# -*- coding: utf-8 -*-
"""Tests for Apache AGE Memory/RDF Quadstore Database pushes."""

import subprocess
import sys
import time
from pathlib import Path
import pytest

from Scripts.infra.age.rdf_quadstore import RDFQuadstore

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


def test_rdf_quadstore_pushes_and_queries():
    """
    Test RDF quadstore operations (insert, query, delete) on the main memory_db.
    """
    # 1. Initialize RDFQuadstore using the main memory_db and graph rdf_quadstore_graph
    store = RDFQuadstore(db_name="memory_db", graph_name="rdf_quadstore_graph")
    store.clear()

    # Define some RDF terms
    s1 = {"type": "iri", "value": "http://example.org/user/alice"}
    s2 = {"type": "iri", "value": "http://example.org/user/bob"}
    
    p_type = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    p_label = "http://www.w3.org/2000/01/rdf-schema#label"
    p_friend = "http://example.org/ontology/hasFriend"

    o_person = {"type": "iri", "value": "http://example.org/ontology/Person"}
    o_alice_lbl = {"type": "literal", "value": "Alice Smith", "datatype": "http://www.w3.org/2001/XMLSchema#string", "lang": "en"}
    o_bob_lbl = {"type": "literal", "value": "Bob Jones", "datatype": "http://www.w3.org/2001/XMLSchema#string", "lang": "en"}

    c_meta = "http://example.org/graphs/metadata"
    c_users = "http://example.org/graphs/users"

    # 2. Add Quads (Pushes to memory_db)
    store.add_quad(s1, p_type, o_person, c_meta)       # Alice is a Person in metadata graph
    store.add_quad(s2, p_type, o_person, c_meta)       # Bob is a Person in metadata graph
    store.add_quad(s1, p_label, o_alice_lbl, c_users)  # Alice's name in users graph
    store.add_quad(s2, p_label, o_bob_lbl, c_users)    # Bob's name in users graph
    store.add_quad(s1, p_friend, s2, c_users)          # Alice friends Bob in users graph

    # 3. Query and verify pushes
    all_quads = store.query_quads()
    assert len(all_quads) == 5

    # Filter by subject
    alice_quads = store.query_quads(subject="http://example.org/user/alice")
    assert len(alice_quads) == 3

    # Filter by predicate
    type_quads = store.query_quads(predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    assert len(type_quads) == 2
    for q in type_quads:
        assert q["object"]["value"] == "http://example.org/ontology/Person"

    # Filter by context
    metadata_quads = store.query_quads(context="http://example.org/graphs/metadata")
    assert len(metadata_quads) == 2

    # Filter by object value (Literal)
    alice_lbl_quads = store.query_quads(obj_value="Alice Smith")
    assert len(alice_lbl_quads) == 1
    assert alice_lbl_quads[0]["object"]["lang"] == "en"
    assert alice_lbl_quads[0]["object"]["type"] == "literal"

    # Filter by object value (Resource IRI)
    friend_quads = store.query_quads(obj_value="http://example.org/user/bob")
    # Only s1 friends s2 has Bob as the object
    assert len(friend_quads) == 1


    # 4. Delete Quads
    # Delete friendship relations
    store.delete_quads(predicate=p_friend)
    
    # Verify friendship is gone
    friend_gone = store.query_quads(predicate=p_friend)
    assert len(friend_gone) == 0
    assert len(store.query_quads()) == 4

    # 5. Clear all
    store.clear()
    assert len(store.query_quads()) == 0
