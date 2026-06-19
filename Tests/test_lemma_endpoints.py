import uuid
from fastapi.testclient import TestClient
from backend.api.api_init import app


def test_save_and_list_connections():
    client = TestClient(app)

    unique = str(uuid.uuid4())
    payload = [
        {"word1": f"w1-{unique}", "word2": f"w2-{unique}", "weight": 42}
    ]

    resp = client.post("/api/lemma/connections", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, dict) and "Successfully" in body.get("message", "")

    # list and assert our connection exists
    list_resp = client.get("/api/lemma/connections?skip=0&limit=200")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert isinstance(data, list)

    found = [d for d in data if d.get("word1") == f"w1-{unique}" and d.get("word2") == f"w2-{unique}" and d.get("weight") == 42]
    assert len(found) >= 1


def test_update_connection():
    client = TestClient(app)
    unique = str(uuid.uuid4())

    # create connection
    payload = [{"word1": f"u1-{unique}", "word2": f"u2-{unique}", "weight": 1}]
    resp = client.post("/api/lemma/connections", json=payload)
    assert resp.status_code == 200

    # find it
    list_resp = client.get("/api/lemma/connections?skip=0&limit=200")
    data = list_resp.json()
    matching = [d for d in data if d.get("word1") == f"u1-{unique}" and d.get("word2") == f"u2-{unique}"]
    assert matching, "created connection not found"
    conn = matching[0]
    conn_id = conn["id"]

    # update weight
    upd = {"weight": 99}
    put_resp = client.put(f"/api/lemma/connections/{conn_id}", json=upd)
    assert put_resp.status_code == 200
    updated = put_resp.json()
    assert updated["weight"] == 99


def test_build_matrix_endpoint():
    client = TestClient(app)
    unique = str(uuid.uuid4())[:8]

    # craft a small text with a unique token pair so we can find it in DB
    a = f"alpha-{unique}"
    b = f"beta-{unique}"
    text = f"{a} {b} {a}"

    resp = client.post("/api/lemma/build", json={"text": text})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, dict) and "Successfully" in body.get("message", "")

    # ensure pair exists in connections list
    list_resp = client.get("/api/lemma/connections?skip=0&limit=500")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert isinstance(data, list)

    found = [d for d in data if {d.get("word1"), d.get("word2")} == {a, b} and d.get("weight", 0) >= 1]
    assert len(found) >= 1, f"Expected to find at least one connection for {a} <-> {b}, got: {data}"


