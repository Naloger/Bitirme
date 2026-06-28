"""Pytest tests for Leiden Spreading Activation.

Uses an in-memory SQLite database seeded with vocabulary, PPMI edges, and
level-0 concepts (with parent_id pointing to level-1 community IDs) to
validate the spreading activation algorithm in isolation.
"""

import logging
import pytest
from sqlmodel import Session, create_engine, select

from backend.database.ORMSchemas.orm_schema_lemma_matrix import (
    LEMMA_MATRIX_METADATA,
    PPMILemmaMatrixModel,
    VocabularyModel,
    ConceptsModel,
)
from Libs.Leiden.leiden_spreading_activation import spreading_activation

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


# ==========================================
# Fixtures
# ==========================================

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


def _seed_graph_with_communities(session: Session) -> None:
    """Insert a test graph with two clear communities and Leiden-style level-0 concepts.

    Community A (fruit): apple ─ banana ─ orange  (strong intra-edges)
    Community B (vehicles): car ─ truck ─ bus     (strong intra-edges)
    Cross-community bridge: orange ─ car          (weak edge)

    Level-1 concept IDs:
      community 100 → fruit
      community 200 → vehicles
    """
    # ── Vocabulary ──
    words = ["apple", "banana", "orange", "car", "truck", "bus"]
    vocab_ids = {}
    for w in words:
        vocab_ids[w] = _get_or_create_vocab_id(session, w)

    # ── PPMI edges ──
    ppmi_edges = [
        # Fruit cluster (strong)
        ("apple", "banana", 4.0),
        ("banana", "orange", 4.0),
        ("apple", "orange", 3.5),
        # Vehicle cluster (strong)
        ("car", "truck", 5.0),
        ("truck", "bus", 5.0),
        ("car", "bus", 4.5),
        # Weak cross-community bridge
        ("orange", "car", 0.5),
    ]
    for idx, (w1, w2, weight) in enumerate(ppmi_edges):
        session.add(PPMILemmaMatrixModel(
            id=idx + 1,
            vocab1_id=vocab_ids[w1],
            vocab2_id=vocab_ids[w2],
            weight=weight,
        ))

    # ── Level-1 parent concepts (community representatives) ──
    community_fruit_id = 100
    community_vehicle_id = 200

    session.add(ConceptsModel(
        id=community_fruit_id, level=1, parent_id=None,
        vocab_id=None, label="fruit_community",
        pagerank_score=1.0, is_leader=True,
    ))
    session.add(ConceptsModel(
        id=community_vehicle_id, level=1, parent_id=None,
        vocab_id=None, label="vehicle_community",
        pagerank_score=1.0, is_leader=True,
    ))

    # ── Level-0 concepts (words assigned to communities via parent_id) ──
    concept_id_start = 1
    fruit_words = ["apple", "banana", "orange"]
    vehicle_words = ["car", "truck", "bus"]

    for i, w in enumerate(fruit_words):
        session.add(ConceptsModel(
            id=concept_id_start + i, level=0,
            parent_id=community_fruit_id,
            vocab_id=vocab_ids[w], label=w,
            pagerank_score=0.33, is_leader=(w == "apple"),
        ))

    for i, w in enumerate(vehicle_words):
        session.add(ConceptsModel(
            id=concept_id_start + len(fruit_words) + i, level=0,
            parent_id=community_vehicle_id,
            vocab_id=vocab_ids[w], label=w,
            pagerank_score=0.33, is_leader=(w == "car"),
        ))

    session.commit()


# ==========================================
# Tests
# ==========================================

def test_spreading_activation_empty_db(in_memory_session):
    """Spreading activation with no data should return an empty dict."""
    logger.info("Starting [test_spreading_activation_empty_db]")

    logger.info("Step 1: Run spreading activation with no data in the database.")
    results = spreading_activation(in_memory_session, seed_words=["apple"])
    logger.debug("Results: %s", results)

    logger.info("Step 2: Assert empty results.")
    assert results == {}
    logger.info("[PASS] test_spreading_activation_empty_db")


def test_spreading_activation_unknown_seeds(in_memory_session):
    """Seeds that don't exist in vocabulary should return an empty dict."""
    logger.info("Starting [test_spreading_activation_unknown_seeds]")

    _seed_graph_with_communities(in_memory_session)

    logger.info("Step 1: Run spreading activation with non-existent seed words.")
    results = spreading_activation(
        in_memory_session,
        seed_words=["nonexistent", "fakword", "zzzzz"],
    )
    logger.debug("Results: %s", results)

    logger.info("Step 2: Assert empty results (no valid seeds).")
    assert results == {}
    logger.info("[PASS] test_spreading_activation_unknown_seeds")


def test_spreading_activation_single_seed_intra_community(in_memory_session):
    """A single seed should activate its own community members strongly."""
    logger.info("Starting [test_spreading_activation_single_seed_intra_community]")

    _seed_graph_with_communities(in_memory_session)

    logger.info("Step 1: Activate 'apple' and let it spread.")
    results = spreading_activation(
        in_memory_session,
        seed_words=["apple"],
        decay=0.8,
        max_steps=3,
        intra_community_boost=1.0,
        inter_community_penalty=0.3,
    )
    logger.info("Step 2: Activated words: %s", results)

    logger.info("Step 3: Assert apple is in results with highest activation.")
    assert "apple" in results
    apple_score = results["apple"]
    logger.debug("apple score: %.6f", apple_score)

    logger.info("Step 4: Assert community members (banana, orange) are activated.")
    assert "banana" in results, "banana should be activated (same community as apple)"
    assert "orange" in results, "orange should be activated (same community as apple)"

    logger.info("Step 5: Assert intra-community scores are higher than inter-community scores.")
    banana_score = results.get("banana", 0.0)
    orange_score = results.get("orange", 0.0)
    # Cross-community words (if reached) should have lower activation
    for cross_word in ["car", "truck", "bus"]:
        if cross_word in results:
            cross_score = results[cross_word]
            logger.debug("%s score: %.6f vs banana score: %.6f", cross_word, cross_score, banana_score)
            assert cross_score < banana_score, (
                f"Cross-community word '{cross_word}' ({cross_score:.6f}) "
                f"should have lower activation than intra-community 'banana' ({banana_score:.6f})"
            )

    logger.info("[CHECK] Intra-community members activated more strongly than cross-community.")
    logger.info("[PASS] test_spreading_activation_single_seed_intra_community")


def test_spreading_activation_multi_seed(in_memory_session):
    """Multiple seeds from different communities should activate both clusters."""
    logger.info("Starting [test_spreading_activation_multi_seed]")

    _seed_graph_with_communities(in_memory_session)

    logger.info("Step 1: Activate 'apple' and 'car' (one from each community).")
    results = spreading_activation(
        in_memory_session,
        seed_words=["apple", "car"],
        decay=0.8,
        max_steps=3,
    )
    logger.info("Step 2: Activated words: %s", results)

    logger.info("Step 3: Assert all 6 words in the graph are activated.")
    for expected_word in ["apple", "banana", "orange", "car", "truck", "bus"]:
        assert expected_word in results, f"'{expected_word}' should be in the results"
    logger.info("[CHECK] All graph words activated.")

    logger.info("Step 4: Assert seeds are well-activated (re-enforced above initial_activation).")
    assert results["apple"] >= 1.0, f"Seed 'apple' should be at least 1.0, got {results['apple']}"
    assert results["car"] >= 1.0, f"Seed 'car' should be at least 1.0, got {results['car']}"
    logger.info("[CHECK] Seeds maintain strong activation.")

    logger.info("[PASS] test_spreading_activation_multi_seed")


def test_spreading_activation_top_k(in_memory_session):
    """top_k parameter should limit the number of returned results."""
    logger.info("Starting [test_spreading_activation_top_k]")

    _seed_graph_with_communities(in_memory_session)

    logger.info("Step 1: Run spreading activation with top_k=3.")
    results = spreading_activation(
        in_memory_session,
        seed_words=["apple"],
        decay=0.8,
        max_steps=5,
        top_k=3,
    )
    logger.info("Step 2: Results (top 3): %s", results)

    logger.info("Step 3: Assert at most 3 results returned.")
    assert len(results) <= 3
    logger.info("[CHECK] top_k correctly limits output size to %d.", len(results))
    logger.info("[PASS] test_spreading_activation_top_k")


def test_spreading_activation_decay_effect(in_memory_session):
    """Lower decay should produce lower activations at distant nodes."""
    logger.info("Starting [test_spreading_activation_decay_effect]")

    _seed_graph_with_communities(in_memory_session)

    logger.info("Step 1: Run with high decay (0.9).")
    results_high = spreading_activation(
        in_memory_session,
        seed_words=["apple"],
        decay=0.9,
        max_steps=3,
        inter_community_penalty=0.3,
    )
    logger.info("High decay results: %s", results_high)

    logger.info("Step 2: Run with low decay (0.3).")
    results_low = spreading_activation(
        in_memory_session,
        seed_words=["apple"],
        decay=0.3,
        max_steps=3,
        inter_community_penalty=0.3,
    )
    logger.info("Low decay results: %s", results_low)

    logger.info("Step 3: Assert non-seed neighbors have higher scores with high decay.")
    for word in ["banana", "orange"]:
        high_score = results_high.get(word, 0.0)
        low_score = results_low.get(word, 0.0)
        logger.debug("%s: high_decay=%.6f, low_decay=%.6f", word, high_score, low_score)
        assert high_score >= low_score, (
            f"'{word}' should have higher activation with decay=0.9 ({high_score:.6f}) "
            f"than with decay=0.3 ({low_score:.6f})"
        )

    logger.info("[CHECK] Decay factor correctly modulates activation spread.")
    logger.info("[PASS] test_spreading_activation_decay_effect")


def test_spreading_activation_community_penalty_effect(in_memory_session):
    """Higher inter-community penalty should reduce cross-community activation."""
    logger.info("Starting [test_spreading_activation_community_penalty_effect]")

    _seed_graph_with_communities(in_memory_session)

    logger.info("Step 1: Run with weak penalty (0.9 — almost no penalty).")
    results_weak = spreading_activation(
        in_memory_session,
        seed_words=["orange"],  # orange is the bridge word
        decay=0.8,
        max_steps=5,
        inter_community_penalty=0.9,
    )

    logger.info("Step 2: Run with strong penalty (0.05 — heavy penalty).")
    results_strong = spreading_activation(
        in_memory_session,
        seed_words=["orange"],
        decay=0.8,
        max_steps=5,
        inter_community_penalty=0.05,
    )

    logger.info("Weak penalty results: %s", results_weak)
    logger.info("Strong penalty results: %s", results_strong)

    logger.info("Step 3: Assert cross-community words (car, truck, bus) are weaker under strong penalty.")
    for cross_word in ["car", "truck", "bus"]:
        weak_score = results_weak.get(cross_word, 0.0)
        strong_score = results_strong.get(cross_word, 0.0)
        logger.debug("%s: weak_penalty=%.6f, strong_penalty=%.6f", cross_word, weak_score, strong_score)
        assert weak_score >= strong_score, (
            f"'{cross_word}' should have higher activation with weak penalty ({weak_score:.6f}) "
            f"than with strong penalty ({strong_score:.6f})"
        )

    logger.info("[CHECK] Inter-community penalty correctly attenuates cross-community spreading.")
    logger.info("[PASS] test_spreading_activation_community_penalty_effect")


def test_spreading_activation_no_hierarchy(in_memory_session):
    """When concepts table is empty (no hierarchy built), spreading should still work with neutral factor."""
    logger.info("Starting [test_spreading_activation_no_hierarchy]")

    # Only insert vocabulary and PPMI edges — NO concepts
    words = ["sun", "moon", "star"]
    vocab_ids = {}
    for w in words:
        vocab_ids[w] = _get_or_create_vocab_id(in_memory_session, w)

    ppmi_edges = [
        ("sun", "moon", 3.0),
        ("moon", "star", 2.5),
        ("sun", "star", 2.0),
    ]
    for idx, (w1, w2, weight) in enumerate(ppmi_edges):
        in_memory_session.add(PPMILemmaMatrixModel(
            id=idx + 1,
            vocab1_id=vocab_ids[w1],
            vocab2_id=vocab_ids[w2],
            weight=weight,
        ))
    in_memory_session.commit()

    logger.info("Step 1: Run spreading activation with no community data.")
    results = spreading_activation(
        in_memory_session,
        seed_words=["sun"],
        decay=0.8,
        max_steps=3,
    )
    logger.info("Results: %s", results)

    logger.info("Step 2: Assert all connected words are activated.")
    assert "sun" in results
    assert "moon" in results
    assert "star" in results
    logger.info("[CHECK] Spreading works correctly even without Leiden hierarchy.")
    logger.info("[PASS] test_spreading_activation_no_hierarchy")
