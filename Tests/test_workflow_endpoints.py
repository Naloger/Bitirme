import unittest.mock as mock
import pytest
from fastapi.testclient import TestClient

from backend.api.api_init import app

client = TestClient(app)

@pytest.fixture
def mock_typesense():
    with mock.patch("backend.api.Endpoints.workflow_endpoints.typesense_client") as mocked:
        yield mocked

@pytest.fixture
def mock_spreading_activation():
    with mock.patch("backend.api.Endpoints.workflow_endpoints.spreading_activation") as mocked:
        yield mocked

@pytest.fixture
def mock_rdf_quadstore():
    with mock.patch("backend.api.Endpoints.workflow_endpoints.RDFQuadstore") as mocked:
        instance = mock.Mock()
        mocked.return_value = instance
        yield instance

def test_raw_input_workflow(mock_typesense, mock_spreading_activation, mock_rdf_quadstore):
    # Setup mocks
    mock_typesense.index_document = mock.AsyncMock(return_value={})
    mock_typesense.bulk_index_documents = mock.AsyncMock(return_value=[])
    
    mock_spreading_activation.return_value = {
        "sun": 1.0,
        "god": 0.8
    }
    
    # Mock RDF quadstore return values
    mock_rdf_quadstore.query_quads.return_value = [
        {
            "subject": {"type": "iri", "value": "http://example.org/sun_god"},
            "predicate": "http://example.org/hasAttribute",
            "object": {"type": "literal", "value": "Sol"},
            "context": "http://example.org/context"
        },
        {
            "subject": {"type": "iri", "value": "http://example.org/moon"},
            "predicate": "http://example.org/hasAttribute",
            "object": {"type": "literal", "value": "Luna"},
            "context": "http://example.org/context"
        }
    ]
    
    payload = {
        "raw_text": "The sun is a roman god.",
        "session_id": "test-session-123",
        "key": "test-key",
        "role": "user"
    }
    
    response = client.post("/api/workflow/raw-input", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["session_id"] == "test-session-123"
    assert "unstructured_page_id" in data
    
    # Verify index_document was called for short-term memory
    mock_typesense.index_document.assert_called_once()
    args, kwargs = mock_typesense.index_document.call_args
    assert args[0] == "session_short_term_memory"
    assert args[1]["content"] == payload["raw_text"]
    assert args[1]["session_id"] == payload["session_id"]
    
    # Verify bulk_index_documents was called for working memory
    mock_typesense.bulk_index_documents.assert_called_once()
    args, kwargs = mock_typesense.bulk_index_documents.call_args
    assert args[0] == "session_working_memory"
    assert len(args[1]) == 1
    assert args[1][0]["subject"] == "http://example.org/sun_god"

def test_raw_input_workflow_malformed_json(mock_typesense, mock_spreading_activation, mock_rdf_quadstore):
    # Setup mocks
    mock_typesense.index_document = mock.AsyncMock(return_value={})
    mock_typesense.bulk_index_documents = mock.AsyncMock(return_value=[])
    
    mock_spreading_activation.return_value = {
        "sun": 1.0
    }
    mock_rdf_quadstore.query_quads.return_value = []
    
    # Send malformed JSON payload with unescaped double quotes inside raw_text
    malformed_json_str = '{\n  "raw_text": "this is a "nested" quote test.",\n  "session_id": "test-session-123"\n}'
    
    response = client.post(
        "/api/workflow/raw-input",
        content=malformed_json_str,
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["session_id"] == "test-session-123"
    assert "unstructured_page_id" in data

