import unittest.mock as mock
import pytest
from fastapi.testclient import TestClient

from backend.api.api_init import app

client = TestClient(app)

@pytest.fixture
def mock_typesense():
    with mock.patch("backend.api.Endpoints.session_endpoints.typesense_client") as mocked:
        yield mocked

def test_add_ego_quad(mock_typesense):
    # Prepare mock async return value
    mock_typesense.index_document = mock.AsyncMock(return_value={
        "id": "quad-1",
        "session_id": "session-abc",
        "subject": "Alice",
        "predicate": "knows",
        "object": "Bob",
        "context": "social",
        "semantic_text": "Alice knows Bob",
        "timestamp": 1234567890
    })
    
    response = client.post(
        "/api/session/session-abc/ego",
        json={
            "subject": "Alice",
            "predicate": "knows",
            "object": "Bob",
            "context": "social"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "quad-1"
    assert data["subject"] == "Alice"
    assert data["predicate"] == "knows"
    assert data["object"] == "Bob"
    assert data["context"] == "social"
    assert data["semantic_text"] == "Alice knows Bob"
    
    # Verify client mock call has generated the semantic_text properly
    mock_typesense.index_document.assert_called_once()
    call_args = mock_typesense.index_document.call_args[0]
    assert call_args[0] == "session_ego"
    assert call_args[1]["subject"] == "Alice"
    assert call_args[1]["session_id"] == "session-abc"
    assert call_args[1]["semantic_text"] == "Alice knows Bob"

def test_bulk_add_ego_quads(mock_typesense):
    mock_typesense.bulk_index_documents = mock.AsyncMock(return_value=[
        {"success": True},
        {"success": True}
    ])
    
    payload = [
        {"subject": "Alice", "predicate": "knows", "object": "Bob"},
        {"subject": "Bob", "predicate": "knows", "object": "Charlie"}
    ]
    
    response = client.post(
        "/api/session/session-abc/ego/bulk",
        json=payload
    )
    
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 2
    assert data[0]["subject"] == "Alice"
    assert data[0]["semantic_text"] == "Alice knows Bob"
    assert data[1]["subject"] == "Bob"
    assert data[1]["semantic_text"] == "Bob knows Charlie"
    
    mock_typesense.bulk_index_documents.assert_called_once()
    assert mock_typesense.bulk_index_documents.call_args[0][0] == "session_ego"
    bulk_docs = mock_typesense.bulk_index_documents.call_args[0][1]
    assert bulk_docs[0]["semantic_text"] == "Alice knows Bob"
    assert bulk_docs[1]["semantic_text"] == "Bob knows Charlie"

def test_list_ego_quads(mock_typesense):
    mock_typesense.search_collection = mock.AsyncMock(return_value={
        "hits": [
            {
                "document": {
                    "id": "1",
                    "session_id": "session-abc",
                    "subject": "Alice",
                    "predicate": "knows",
                    "object": "Bob",
                    "context": "social",
                    "semantic_text": "Alice knows Bob",
                    "timestamp": 1234567890
                }
            }
        ]
    })
    
    response = client.get(
        "/api/session/session-abc/ego",
        params={"subject": "Alice", "limit": 10}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["subject"] == "Alice"
    assert data[0]["semantic_text"] == "Alice knows Bob"
    
    mock_typesense.search_collection.assert_called_once()
    search_args = mock_typesense.search_collection.call_args[0][1]
    assert "session_id:=session-abc" in search_args["filter_by"]
    assert "subject:=Alice" in search_args["filter_by"]
    assert search_args["per_page"] == 10
    assert "semantic_text" in search_args["query_by"]

def test_search_ego_quads_hybrid(mock_typesense):
    mock_typesense.search_collection = mock.AsyncMock(return_value={
        "found": 1,
        "search_time_ms": 5,
        "hits": [
            {
                "document": {
                    "id": "1",
                    "session_id": "session-abc",
                    "subject": "Alice",
                    "predicate": "knows",
                    "object": "Bob",
                    "context": "",
                    "semantic_text": "Alice knows Bob",
                    "timestamp": 1234567890
                },
                "highlight": {},
                "text_match": 100,
                "vector_distance": 0.12
            }
        ]
    })
    
    response = client.post(
        "/api/session/session-abc/ego/search",
        json={
            "q": "Alice",
            "vector": [0.1] * 1536,
            "limit": 5
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["found"] == 1
    assert len(data["hits"]) == 1
    assert data["hits"][0]["vector_distance"] == 0.12
    assert data["hits"][0]["document"]["semantic_text"] == "Alice knows Bob"
    
    mock_typesense.search_collection.assert_called_once()
    search_args = mock_typesense.search_collection.call_args[0][1]
    assert search_args["q"] == "Alice"
    assert "vector_query" in search_args
    assert "embedding" in search_args["vector_query"]
    assert "semantic_text" in search_args["query_by"]

def test_delete_ego_quad_unauthorized(mock_typesense):
    mock_typesense.get_document = mock.AsyncMock(return_value={
        "id": "quad-1",
        "session_id": "session-other",
        "subject": "Alice",
        "predicate": "knows",
        "object": "Bob",
        "semantic_text": "Alice knows Bob"
    })
    mock_typesense.delete_document = mock.AsyncMock()
    
    response = client.delete("/api/session/session-abc/ego/quad-1")
    assert response.status_code == 403
    assert "Unauthorized" in response.json()["detail"]
    mock_typesense.delete_document.assert_not_called()

def test_delete_ego_quad_success(mock_typesense):
    mock_typesense.get_document = mock.AsyncMock(return_value={
        "id": "quad-1",
        "session_id": "session-abc",
        "subject": "Alice",
        "predicate": "knows",
        "object": "Bob",
        "semantic_text": "Alice knows Bob"
    })
    mock_typesense.delete_document = mock.AsyncMock()
    
    response = client.delete("/api/session/session-abc/ego/quad-1")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_typesense.delete_document.assert_called_once_with("session_ego", "quad-1")


# --- SHORT-TERM MEMORY TESTS ---

def test_add_short_term_memory(mock_typesense):
    mock_typesense.index_document = mock.AsyncMock(return_value={
        "id": "mem-1",
        "session_id": "session-abc",
        "key": "user_profile",
        "content": "Alice is a doctor.",
        "role": "user",
        "timestamp": 1234567890
    })
    
    response = client.post(
        "/api/session/session-abc/short-term-memory",
        json={
            "key": "user_profile",
            "content": "Alice is a doctor.",
            "role": "user"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "mem-1"
    assert data["content"] == "Alice is a doctor."
    assert data["role"] == "user"

def test_list_short_term_memory(mock_typesense):
    mock_typesense.search_collection = mock.AsyncMock(return_value={
        "hits": [
            {
                "document": {
                    "id": "mem-1",
                    "session_id": "session-abc",
                    "key": "chat_history",
                    "content": "Hello",
                    "role": "assistant",
                    "timestamp": 1234567890
                }
            }
        ]
    })
    
    response = client.get(
        "/api/session/session-abc/short-term-memory",
        params={"role": "assistant"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["content"] == "Hello"
    
    search_args = mock_typesense.search_collection.call_args[0][1]
    assert "role:=assistant" in search_args["filter_by"]

def test_clear_working_memory(mock_typesense):
    mock_typesense.delete_documents_by_query = mock.AsyncMock(return_value={"num_deleted": 4})
    
    response = client.delete("/api/session/session-abc/working-memory")
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 4
    mock_typesense.delete_documents_by_query.assert_called_once_with("session_working_memory", "session_id:=session-abc")
