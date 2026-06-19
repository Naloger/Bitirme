import uuid
from fastapi.testclient import TestClient
from backend.api.api_init import app


def test_post_and_get_matrix_connections():
    client = TestClient(app)

    unique = str(uuid.uuid4())[:8]
    a = f"alpha-{unique}"
    b = f"beta-{unique}"
    c = f"gamma-{unique}"

    payload = [
        {"word1": a, "word2": b, "weight": 3},
        {"word1": b, "word2": c, "weight": 1},
    ]

    post_resp = client.post("/api/lemma/connections", json=payload)
    assert post_resp.status_code == 200
    body = post_resp.json()
    assert isinstance(body, dict) and "Successfully" in body.get("message", "")

    list_resp = client.get("/api/lemma/connections?skip=0&limit=500")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert isinstance(data, list)

    # Ensure both connections exist in the returned data
    pair_ab = [d for d in data if d.get("word1") == a and d.get("word2") == b and d.get("weight") == 3]
    pair_bc = [d for d in data if d.get("word1") == b and d.get("word2") == c and d.get("weight") == 1]
    assert len(pair_ab) >= 1, f"Expected to find connection {a} -> {b}"
    assert len(pair_bc) >= 1, f"Expected to find connection {b} -> {c}"

    # Fetch single connection by id and verify
    conn = pair_ab[0]
    conn_id = conn["id"]
    get_resp = client.get(f"/api/lemma/connections/{conn_id}")
    assert get_resp.status_code == 200
    single = get_resp.json()
    assert single["word1"] == a and single["word2"] == b and single["weight"] == 3

