import pytest
from fastapi.testclient import TestClient
from backend.api.api_init import app

client = TestClient(app)

def test_unstructured_page_crud():
    # 1. Create unstructured page
    create_payload = {
        "raw_text": "Sample raw text to be lemmatized.",
        "predicted_output": "sample raw text to be lemmatized",
        "prediction_error": 0.05,
        "transformed_to_matrix": True,
        "lemmatized_words": ["sample", "raw", "text", "lemmatize"]
    }
    
    response = client.post("/api/page/unstructured-pages", json=create_payload)
    assert response.status_code == 200
    created_data = response.json()
    
    assert "id" in created_data
    page_id = created_data["id"]
    assert created_data["raw_text"] == create_payload["raw_text"]
    assert created_data["predicted_output"] == create_payload["predicted_output"]
    assert created_data["prediction_error"] == create_payload["prediction_error"]
    assert created_data["transformed_to_matrix"] is True
    assert created_data["lemmatized_words"] == create_payload["lemmatized_words"]
    
    # 2. Get the unstructured page
    response = client.get(f"/api/page/unstructured-pages/{page_id}")
    assert response.status_code == 200
    retrieved_data = response.json()
    assert retrieved_data["id"] == page_id
    assert retrieved_data["transformed_to_matrix"] is True
    assert retrieved_data["lemmatized_words"] == create_payload["lemmatized_words"]
    
    # 3. Update the unstructured page
    update_payload = {
        "lemmatized_words": ["sample", "lemmatized"],
        "transformed_to_matrix": False
    }
    response = client.put(f"/api/page/unstructured-pages/{page_id}", json=update_payload)
    assert response.status_code == 200
    updated_data = response.json()
    assert updated_data["id"] == page_id
    assert updated_data["transformed_to_matrix"] is False
    assert updated_data["lemmatized_words"] == update_payload["lemmatized_words"]
    # other fields should remain unchanged
    assert updated_data["raw_text"] == create_payload["raw_text"]
    
    # 4. Get all unstructured pages
    response = client.get("/api/page/unstructured-pages")
    assert response.status_code == 200
    all_pages = response.json()
    assert len(all_pages) > 0
    # Find our page in the list
    matched = [p for p in all_pages if p["id"] == page_id]
    assert len(matched) == 1
    assert matched[0]["lemmatized_words"] == update_payload["lemmatized_words"]
