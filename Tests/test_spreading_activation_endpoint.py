import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine
from sqlalchemy.pool import StaticPool
from backend.api.api_init import app, get_lemma_matrix_session
from backend.database.ORMSchemas.orm_schema_lemma_matrix import (
    LEMMA_MATRIX_METADATA,
    VocabularyModel,
    PPMILemmaMatrixModel
)

client = TestClient(app)

@pytest.fixture
def mock_lemma_session():
    """Create in-memory SQLite database specifically for endpoint testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    LEMMA_MATRIX_METADATA.create_all(engine)
    with Session(engine) as session:
        # Seed dummy data
        v_sun = VocabularyModel(id=1, word="sun")
        v_god = VocabularyModel(id=2, word="god")
        session.add(v_sun)
        session.add(v_god)
        session.flush()

        ppmi = PPMILemmaMatrixModel(id=1, vocab1_id=1, vocab2_id=2, weight=4.0)
        session.add(ppmi)
        session.commit()
        
        # Keep session alive for the request thread
        yield session

def test_spreading_activation_endpoint(mock_lemma_session):
    # Override the dependency to use our in-memory test database
    app.dependency_overrides[get_lemma_matrix_session] = lambda: mock_lemma_session

    try:
        # Request with a seed word containing casing & punctuation to test robust matching
        response = client.post(
            "/api/lemma_matrix/spreading_activation",
            json={
                "seed_words": ["Sun."],
                "decay": 0.8,
                "firing_threshold": 0.01,
                "max_steps": 3,
                "initial_activation": 1.0
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify seed_words are returned as-is
        assert data["seed_words"] == ["Sun."]
        
        # Verify total results
        results = data["results"]
        assert len(results) == 2
        
        # Verify that they are split into seed_results and spreaded_results
        seed_res = data["seed_results"]
        spreaded_res = data["spreaded_results"]
        
        # The seed word 'sun' should be in seed_results
        assert len(seed_res) == 1
        assert seed_res[0]["word"] == "sun"
        assert seed_res[0]["score"] >= 1.0
        
        # The spreaded word 'god' should be in spreaded_results
        assert len(spreaded_res) == 1
        assert spreaded_res[0]["word"] == "god"
        assert spreaded_res[0]["score"] > 0.0
        
    finally:
        # Clean up dependency override
        app.dependency_overrides.clear()
