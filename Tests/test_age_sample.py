import subprocess
import sys
import time
from pathlib import Path

import pytest

from Config.config import AGE_MEMORY_DB, AGE_RDF_GRAPH
from Scripts.infra.age.rdf_quadstore import RDFQuadstore


def safe_print(text: str):
    """Safely prints strings containing emojis without crashing on restricted Windows console codepages."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(text.encode(encoding, errors="replace").decode(encoding))


def run_infra_start_script():
    """Executes Scripts/infra/start_infra.py via subprocess to ensure container stack is up."""
    project_root = Path(__file__).resolve().parent.parent
    script_path = project_root / "Scripts" / "infra" / "start_infra.py"

    safe_print(f"\n[INFO] Booting infrastructure stack using: {script_path}...")
    res = subprocess.run(
        [sys.executable, str(script_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )

    if res.returncode != 0:
        safe_print(f"[WARN] start_infra.py returned exit code {res.returncode}.")
        safe_print(f"Error details:\n{res.stderr}")
    else:
        safe_print("[SUCCESS] start_infra.py executed successfully.")
        safe_print(res.stdout)


@pytest.fixture(scope="session", autouse=True)
def setup_infrastructure():
    """Ensure docker/podman infrastructure is running before tests."""
    run_infra_start_script()
    print("[INFO] Waiting for PostgreSQL/Apache AGE service to initialize...")
    time.sleep(3)


def test_create_sample_age_data():
    store = RDFQuadstore(db_name=AGE_MEMORY_DB, graph_name=AGE_RDF_GRAPH)

    # Start from a clean graph so this test is deterministic.
    store.clear()
    assert len(store.query_quads()) == 0

    s1 = {"type": "iri", "value": "http://example.org/user/alice"}
    s2 = {"type": "iri", "value": "http://example.org/user/bob"}

    p_type = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    p_label = "http://www.w3.org/2000/01/rdf-schema#label"
    p_friend = "http://example.org/ontology/hasFriend"

    o_person = {"type": "iri", "value": "http://example.org/ontology/Person"}
    o_alice_lbl = {
        "type": "literal",
        "value": "Alice Smith",
        "datatype": "http://www.w3.org/2001/XMLSchema#string",
        "lang": "en",
    }
    o_bob_lbl = {
        "type": "literal",
        "value": "Bob Jones",
        "datatype": "http://www.w3.org/2001/XMLSchema#string",
        "lang": "en",
    }

    c_meta = "http://example.org/graphs/metadata"
    c_users = "http://example.org/graphs/users"

    store.add_quad(s1, p_type, o_person, c_meta)
    store.add_quad(s2, p_type, o_person, c_meta)
    store.add_quad(s1, p_label, o_alice_lbl, c_users)
    store.add_quad(s2, p_label, o_bob_lbl, c_users)
    store.add_quad(s1, p_friend, s2, c_users)

    all_quads = store.query_quads()
    assert len(all_quads) == 5

    alice_quads = store.query_quads(subject="http://example.org/user/alice")
    assert len(alice_quads) == 3

    type_quads = store.query_quads(predicate=p_type)
    assert len(type_quads) == 2
    for q in type_quads:
        assert q["object"]["value"] == "http://example.org/ontology/Person"

    metadata_quads = store.query_quads(context=c_meta)
    assert len(metadata_quads) == 2

    alice_lbl_quads = store.query_quads(obj_value="Alice Smith")
    assert len(alice_lbl_quads) == 1
    assert alice_lbl_quads[0]["object"]["lang"] == "en"
    assert alice_lbl_quads[0]["object"]["type"] == "literal"

    friend_quads = store.query_quads(obj_value="http://example.org/user/bob")
    assert len(friend_quads) == 1

    store.delete_quads(predicate=p_friend)
    assert len(store.query_quads(predicate=p_friend)) == 0
    assert len(store.query_quads()) == 4
