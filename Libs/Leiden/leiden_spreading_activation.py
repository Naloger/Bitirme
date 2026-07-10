"""Spreading Activation over the PPMI graph, modulated by Leiden community structure.

Spreading Activation (SA) is a cognitive-inspired search technique where seed
nodes are activated and activation energy propagates through the graph.  Combined
with Leiden communities the propagation is modulated by community boundaries:
activation spreads faster within communities and attenuates across them.

Usage:
    from Libs.Leiden.leiden_spreading_activation import spreading_activation

    results = spreading_activation(
        session=db_session,
        seed_words=["sun", "roman", "god"],
        decay=0.8,
        max_steps=5,
        top_k=20,
    )
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set

from sqlmodel import Session, select

from backend.database.ORMSchemas.orm_schema_lemma_matrix import (
    PPMILemmaMatrixModel,
    VocabularyModel,
    ConceptsModel,
    ConceptConnectionsModel,
)

logger = logging.getLogger(__name__)


def spreading_activation(
    session: Session,
    seed_words: List[str],
    decay: float = 0.8,
    firing_threshold: float = 0.01,
    max_steps: int = 5,
    hierarchy_weight: float = 1.0,
    intra_community_boost: float = 1.0,
    inter_community_penalty: float = 0.3,
    initial_activation: float = 1.0,
    top_k: Optional[int] = None,
) -> Dict[str, float]:
    """Perform Spreading Activation over the PPMI + Leiden Hierarchy graph.

    Nodes can be words (Vocabulary) or Leiden communities (Concepts).
    Activation spreads across PPMI edges and UP/DOWN the hierarchy branches.

    Args:
        session: Active SQLModel session connected to lemma_matrix.db.
        seed_words: List of words to activate initially.
        decay: Decay factor per hop (0 < decay <= 1).
        firing_threshold: Minimum activation a node must hold to propagate.
        max_steps: Maximum number of propagation iterations.
        hierarchy_weight: Multiplier for traversing up/down the Leiden hierarchy branches.
        intra_community_boost: Multiplier for direct PPMI edges within the same Level-1 community.
        inter_community_penalty: Multiplier for direct PPMI edges crossing community boundaries.
        initial_activation: Starting activation value assigned to each seed node.
        top_k: If set, return only the top-K activated words.

    Returns:
        Dictionary mapping word → final activation score, sorted descending.
    """
    # 1. Load vocabulary look-ups
    vocab_records = session.exec(select(VocabularyModel)).all()
    word_to_id: Dict[str, int] = {}
    id_to_word: Dict[int, str] = {}
    for v in vocab_records:
        if v.id is not None and v.word:
            word_to_id[v.word] = v.id
            word_to_id[v.word.lower().strip()] = v.id
            id_to_word[v.id] = v.word

    # 2. Resolve seed words → vocab IDs using Lemmatizer pipeline
    from Libs.Lemmatizer.lemma_matrix import LemmaMatrixBuilder
    builder = LemmaMatrixBuilder()

    seed_ids: Set[int] = set()
    for word in seed_words:
        tokens = builder.tokenize(word)
        found = False
        for token in tokens:
            vid = word_to_id.get(token)
            if vid is not None:
                seed_ids.add(vid)
                found = True
        if not found:
            logger.warning("Seed word '%s' not found in vocabulary. Skipping.", word)

    if not seed_ids:
        return {}

    # 3. Load Level-1 community mapping for PPMI edge modulation
    level0_concepts = session.exec(
        select(ConceptsModel).where(ConceptsModel.level == 0)
    ).all()
    vocab_to_community: Dict[int, int] = {}
    for concept in level0_concepts:
        if concept.vocab_id is not None and concept.parent_id is not None:
            vocab_to_community[concept.vocab_id] = concept.parent_id

    # 4. Build Unified Adjacency List
    # Namespace nodes: "v:{id}" for vocabulary, "c:{id}" for concepts
    adjacency: Dict[str, List[tuple[str, float]]] = defaultdict(list)

    # 4a. Add PPMI Edges
    ppmi_edges = session.exec(select(PPMILemmaMatrixModel)).all()
    for edge in ppmi_edges:
        w = float(edge.weight)
        if w <= 0:
            continue
            
        # Apply community modulation to direct PPMI edges
        comm1 = vocab_to_community.get(edge.vocab1_id)
        comm2 = vocab_to_community.get(edge.vocab2_id)
        if comm1 is not None and comm2 is not None:
            factor = intra_community_boost if comm1 == comm2 else inter_community_penalty
        else:
            factor = 1.0
            
        w_mod = w * factor
        n1 = f"v:{edge.vocab1_id}"
        n2 = f"v:{edge.vocab2_id}"
        adjacency[n1].append((n2, w_mod))
        adjacency[n2].append((n1, w_mod))

    # 4b. Add Hierarchy Edges (Parent <-> Child)
    all_concepts = session.exec(select(ConceptsModel)).all()
    for c in all_concepts:
        if c.parent_id is None:
            continue
            
        # Modulate hierarchy traversal by the child's PageRank (leader attraction)
        pr_score = c.pagerank_score if c.pagerank_score is not None else 1.0
        w_hier = hierarchy_weight * pr_score
        
        parent_node = f"c:{c.parent_id}"
        if c.level == 0 and c.vocab_id is not None:
            child_node = f"v:{c.vocab_id}"
        else:
            child_node = f"c:{c.id}"
            
        adjacency[child_node].append((parent_node, w_hier))
        adjacency[parent_node].append((child_node, w_hier))

    # 4c. Add Concept-Concept Connections (Higher level lateral edges)
    all_conns = session.exec(select(ConceptConnectionsModel)).all()
    for conn in all_conns:
        w_conn = float(conn.weight)
        n1 = f"c:{conn.node1_id}"
        n2 = f"c:{conn.node2_id}"
        adjacency[n1].append((n2, w_conn))
        adjacency[n2].append((n1, w_conn))

    # 5. Initialize activations
    activations: Dict[str, float] = defaultdict(float)
    for sid in seed_ids:
        activations[f"v:{sid}"] = initial_activation

    logger.info(
        "Spreading activation: %d seeds, max_steps=%d, hierarchy_weight=%.2f",
        len(seed_ids), max_steps, hierarchy_weight
    )

    # 6. Iterative spreading
    for step in range(max_steps):
        new_activations: Dict[str, float] = defaultdict(float)
        active_count = 0

        for node_id, activation in activations.items():
            if activation < firing_threshold:
                continue
            active_count += 1

            for neighbor_id, weight in adjacency.get(node_id, []):
                spread = decay * weight * activation
                new_activations[neighbor_id] += spread

        if active_count == 0:
            break

        # Merge: keep the higher of existing or newly received activation
        for node_id, new_val in new_activations.items():
            activations[node_id] = max(activations[node_id], new_val)

        # Re-enforce seed nodes
        for sid in seed_ids:
            seed_key = f"v:{sid}"
            activations[seed_key] = max(activations[seed_key], initial_activation)

    # 7. Build sorted result dict (filtering out concept nodes)
    results: Dict[str, float] = {}
    for node_id, score in activations.items():
        if node_id.startswith("v:") and score > firing_threshold:
            vid = int(node_id[2:])
            word = id_to_word.get(vid)
            if word:
                results[word] = round(score, 6)

    sorted_results = dict(sorted(results.items(), key=lambda x: x[1], reverse=True))

    if top_k is not None:
        sorted_results = dict(list(sorted_results.items())[:top_k])

    return sorted_results
