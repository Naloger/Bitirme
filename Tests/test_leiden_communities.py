import logging
import pytest
from sqlmodel import Session, create_engine, select

from backend.database.ORMSchemas.orm_schema_lemma_matrix import (
    LEMMA_MATRIX_METADATA,
    PPMILemmaMatrixModel,
    VocabularyModel,
)
from Libs.Leiden.leiden_communities import detect_communities_leiden

# ==========================================
# Enhanced Logging Configuration
# ==========================================
class LogFormatter(logging.Formatter):
    """Custom formatter to make test results pop with ANSI colors."""
    GREY = "\x1b[38;20m"
    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    RESET = "\x1b[0m"
    FORMAT_STR = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def format(self, record):
        if "[PASS]" in str(record.msg):
            log_fmt = self.GREEN + self.FORMAT_STR + self.RESET
        elif "[FAIL]" in str(record.msg) or record.levelno >= logging.ERROR:
            log_fmt = self.RED + self.FORMAT_STR + self.RESET
        elif record.levelno == logging.WARNING:
            log_fmt = self.YELLOW + self.FORMAT_STR + self.RESET
        else:
            log_fmt = self.GREY + self.FORMAT_STR + self.RESET

        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(LogFormatter())
    logger.addHandler(ch)

logger.propagate = False


@pytest.fixture
def in_memory_session():
    """Create a clean, isolated in-memory SQLite database session for testing."""
    logger.debug("[SETUP] Initializing in-memory SQLite database engine.")
    engine = create_engine("sqlite:///:memory:")
    logger.debug("[SETUP] Creating schema tables from LEMMA_MATRIX_METADATA.")
    LEMMA_MATRIX_METADATA.create_all(engine)
    with Session(engine) as session:
        yield session
    logger.debug("[TEARDOWN] Disposing of in-memory database session.")


def _get_or_create_vocab_id(session: Session, word: str) -> int:
    """Helper to get or create vocabulary entry and return its ID in tests."""
    existing = session.exec(select(VocabularyModel).where(VocabularyModel.word == word)).first()
    if existing:
        return existing.id
    new_vocab = VocabularyModel(word=word)
    session.add(new_vocab)
    session.flush()
    return new_vocab.id


def test_leiden_empty_db(in_memory_session):
    logger.info("Starting [test_leiden_empty_db]")
    
    logger.info("Step 1: Check that PPMILemmaMatrixModel table is initially empty.")
    records = in_memory_session.exec(select(PPMILemmaMatrixModel)).all()
    logger.debug("Active record count: %d", len(records))
    assert len(records) == 0
    
    logger.info("Step 2: Run detect_communities_leiden on the empty database state.")
    communities = detect_communities_leiden(in_memory_session)
    logger.debug("Returned communities: %s", communities)
    
    logger.info("Step 3: Assert that returned communities dictionary is empty.")
    assert communities == {}
    logger.info("[CHECK] Empty database correctly returned an empty dictionary.")
    logger.info("[PASS] test_leiden_empty_db")


def test_leiden_basic_communities(in_memory_session):
    logger.info("Starting [test_leiden_basic_communities]")
    
    # Define two distinct clusters
    # Cluster 1 (Fruit): apple - banana - orange
    # Cluster 2 (Vehicles): car - truck - bus
    test_edges = [
        # Fruit cluster
        ("apple", "banana", 4.0),
        ("banana", "orange", 4.0),
        ("apple", "orange", 4.0),
        # Vehicle cluster
        ("car", "truck", 5.0),
        ("truck", "bus", 5.0),
        ("car", "bus", 5.0),
    ]
    
    logger.info("Step 1: Inserting PPMILemmaMatrixModel mock records representing two distinct clusters:")
    logger.info("  Cluster 1 (Fruit): apple, banana, orange")
    logger.info("  Cluster 2 (Vehicles): car, truck, bus")
    for idx, (w1, w2, weight) in enumerate(test_edges):
        v1_id = _get_or_create_vocab_id(in_memory_session, w1)
        v2_id = _get_or_create_vocab_id(in_memory_session, w2)
        record = PPMILemmaMatrixModel(id=idx + 1, vocab1_id=v1_id, vocab2_id=v2_id, weight=weight)
        in_memory_session.add(record)
        logger.debug("   [DB INSERT] record id=%d: %s (id=%d) <-> %s (id=%d), weight=%.2f", idx + 1, w1, v1_id, w2, v2_id, weight)
        
    logger.info("Step 2: Committing transactions to SQLite database.")
    in_memory_session.commit()
    
    logger.info("Step 3: Invoking detect_communities_leiden with partition_type='modularity', seed=42.")
    communities = detect_communities_leiden(in_memory_session, seed=42)
    logger.info("Detected communities from algorithm: %s", communities)
    
    logger.info("Step 4: Asserting we found exactly 2 communities.")
    assert len(communities) == 2
    logger.debug("Assertion passed: length is exactly 2.")
    
    logger.info("Step 5: Sorting and validating membership values of detected communities.")
    community_values = list(communities.values())
    community_values.sort(key=lambda x: x[0])
    
    logger.info("Step 6: Comparing actual groupings with expected groupings.")
    logger.debug("Expected Fruit cluster: ['apple', 'banana', 'orange'] | Actual: %s", community_values[0])
    assert community_values[0] == ["apple", "banana", "orange"]
    logger.info("[CHECK] Fruit cluster grouping verified.")
    
    logger.debug("Expected Vehicle cluster: ['bus', 'car', 'truck'] | Actual: %s", community_values[1])
    assert community_values[1] == ["bus", "car", "truck"]
    logger.info("[CHECK] Vehicle cluster grouping verified.")
    
    logger.info("[PASS] test_leiden_basic_communities")


def test_leiden_resolution_cpm(in_memory_session):
    logger.info("Starting [test_leiden_resolution_cpm]")
    
    test_edges = [
        ("apple", "banana", 3.0),
        ("banana", "orange", 3.0),
        ("car", "truck", 3.0),
    ]
    
    logger.info("Step 1: Inserting edges with identical weights to test resolution changes under CPM:")
    for idx, (w1, w2, weight) in enumerate(test_edges):
        v1_id = _get_or_create_vocab_id(in_memory_session, w1)
        v2_id = _get_or_create_vocab_id(in_memory_session, w2)
        record = PPMILemmaMatrixModel(id=idx + 1, vocab1_id=v1_id, vocab2_id=v2_id, weight=weight)
        in_memory_session.add(record)
        logger.debug("   [DB INSERT] record id=%d: %s (id=%d) <-> %s (id=%d), weight=%.2f", idx + 1, w1, v1_id, w2, v2_id, weight)
        
    logger.info("Step 2: Committing transaction to SQLite.")
    in_memory_session.commit()
    
    logger.info("Step 3: Running detect_communities_leiden using partition_type='cpm', resolution_parameter=0.5, seed=100.")
    communities = detect_communities_leiden(
        in_memory_session,
        partition_type="cpm",
        resolution_parameter=0.5,
        seed=100,
    )
    logger.info("Detected communities (CPM): %s", communities)
    
    logger.info("Step 4: Verify that partitioning was calculated and returned communities.")
    assert len(communities) > 0
    logger.info("[CHECK] CPM partitioning executed successfully with custom resolution.")
    logger.info("[PASS] test_leiden_resolution_cpm")


def test_leiden_min_size_filter(in_memory_session):
    logger.info("Starting [test_leiden_min_size_filter]")
    
    # Define a cluster of 3 words, and an isolated edge of 2 words
    test_edges = [
        # Cluster of 3
        ("apple", "banana", 4.0),
        ("banana", "orange", 4.0),
        ("apple", "orange", 4.0),
        # Isolated pair (size 2)
        ("dog", "cat", 5.0),
    ]
    
    logger.info("Step 1: Inserting mock edge data containing a size-3 cluster and a size-2 cluster:")
    for idx, (w1, w2, weight) in enumerate(test_edges):
        v1_id = _get_or_create_vocab_id(in_memory_session, w1)
        v2_id = _get_or_create_vocab_id(in_memory_session, w2)
        record = PPMILemmaMatrixModel(id=idx + 1, vocab1_id=v1_id, vocab2_id=v2_id, weight=weight)
        in_memory_session.add(record)
        logger.debug("   [DB INSERT] record id=%d: %s (id=%d) <-> %s (id=%d), weight=%.2f", idx + 1, w1, v1_id, w2, v2_id, weight)
        
    logger.info("Step 2: Committing transaction to SQLite.")
    in_memory_session.commit()
    
    logger.info("Step 3: Invoking detect_communities_leiden with min_community_size=3.")
    communities = detect_communities_leiden(
        in_memory_session,
        min_community_size=3,
        seed=42,
    )
    logger.info("Detected communities (min_size=3): %s", communities)
    
    logger.info("Step 4: Asserting that only the size-3 community (fruit cluster) remains.")
    assert len(communities) == 1
    assert list(communities.values())[0] == ["apple", "banana", "orange"]
    
    logger.info("[CHECK] Community of size 2 ('cat'-'dog') was correctly filtered out when min_size=3.")
    logger.info("[PASS] test_leiden_min_size_filter")


def test_leiden_seed_reproducibility(in_memory_session):
    logger.info("Starting [test_leiden_seed_reproducibility]")
    
    # We create two distinct cliques connected by a single weak link
    test_edges = []
    idx = 1
    
    logger.info("Step 1: Generating a double-clique test graph with a weak boundary link:")
    logger.info("   Adding Clique 1: {A, B, C, D}")
    for u in ["A", "B", "C", "D"]:
        for v in ["A", "B", "C", "D"]:
            if u < v:
                test_edges.append((u, v, 2.0))
                
    logger.info("   Adding Clique 2: {E, F, G, H}")
    for u in ["E", "F", "G", "H"]:
        for v in ["E", "F", "G", "H"]:
            if u < v:
                test_edges.append((u, v, 2.0))
                
    logger.info("   Adding Weak boundary link: D <-> E (weight=0.1)")
    test_edges.append(("D", "E", 0.1))
    
    for w1, w2, weight in test_edges:
        v1_id = _get_or_create_vocab_id(in_memory_session, w1)
        v2_id = _get_or_create_vocab_id(in_memory_session, w2)
        record = PPMILemmaMatrixModel(id=idx, vocab1_id=v1_id, vocab2_id=v2_id, weight=weight)
        in_memory_session.add(record)
        idx += 1
    in_memory_session.commit()
    logger.info("Step 2: Successfully inserted %d mock edges and committed to SQLite.", len(test_edges))
    
    logger.info("Step 3: Running Leiden detection (Run 1) with seed=1234.")
    communities_1 = detect_communities_leiden(in_memory_session, seed=1234)
    logger.info("Run 1 Communities output: %s", communities_1)
    
    logger.info("Step 4: Running Leiden detection (Run 2) with seed=1234.")
    communities_2 = detect_communities_leiden(in_memory_session, seed=1234)
    logger.info("Run 2 Communities output: %s", communities_2)
    
    logger.info("Step 5: Verifying Run 1 is identical to Run 2.")
    assert communities_1 == communities_2
    logger.info("[CHECK] Consistent community structures obtained using seed.")
    logger.info("[PASS] test_leiden_seed_reproducibility")
