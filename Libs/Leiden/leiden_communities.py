import logging
from typing import Any, Dict, List, Optional, cast

import igraph as ig
import leidenalg as la
from sqlmodel import Session, select

from sqlalchemy.orm import aliased
from backend.database.ORMSchemas.orm_schema_lemma_matrix import (
    PPMILemmaMatrixModel,
    VocabularyModel,
)

logger = logging.getLogger(__name__)


def detect_communities_leiden(
    session: Session,
    partition_type: str = "modularity",
    resolution_parameter: Optional[float] = None,
    seed: Optional[int] = None,
    min_community_size: int = 1,
) -> Dict[int, List[str]]:
    """Detect word communities (clusters) in the PPMI lemma matrix using the Leiden algorithm.

    Args:
        session: An active SQLModel session to query the database.
        partition_type: The quality function to optimize. Supported values:
            - 'modularity': Standard modularity optimization (default).
            - 'cpm': Constant Potts Model.
        resolution_parameter: The resolution parameter. If None:
            - For 'modularity', default is 1.0.
            - For 'cpm', default is 0.1.
            Adjust resolution to get smaller/larger communities.
        seed: Random seed for the Leiden algorithm (ensures reproducibility).
        min_community_size: Minimum number of words required in a community to keep it.

    Returns:
        A dictionary mapping community IDs (0-indexed) to lists of words (lemmas) in that community.
        If the database table is empty, returns an empty dictionary.
    """
    logger.info("Fetching PPMI lemma matrix records from database...")
    v1 = aliased(VocabularyModel)
    v2 = aliased(VocabularyModel)
    
    statement = (
        select(
            cast(Any, v1.word).label("word1"),
            cast(Any, v2.word).label("word2"),
            PPMILemmaMatrixModel.weight
        )
        .join(cast(Any, v1), onclause=cast(Any, PPMILemmaMatrixModel.vocab1_id == v1.id))
        .join(cast(Any, v2), onclause=cast(Any, PPMILemmaMatrixModel.vocab2_id == v2.id))
    )
    records = session.exec(statement).all()

    if not records:
        logger.warning("No records found in ppmi_lemma_matrix table. Returning empty community dictionary.")
        return {}

    # Extract unique words to assign consecutive integer indices for igraph
    unique_words = set()
    edges_raw = []

    for word1, word2, weight_raw in records:
        weight = float(weight_raw)
        
        # Leiden requires positive weights (or zero is ignored); check weight validity
        if weight <= 0:
            continue
            
        unique_words.add(word1)
        unique_words.add(word2)
        edges_raw.append((word1, word2, weight))

    if not unique_words:
        logger.warning("No valid edges with positive weights found. Returning empty community dictionary.")
        return {}

    logger.info(
        "Graph construction: %d unique words (vertices), %d valid connections (edges)",
        len(unique_words),
        len(edges_raw),
    )

    # Map words to consecutive integer IDs for igraph
    words_list = list(sorted(unique_words))
    word_to_id = {word: idx for idx, word in enumerate(words_list)}

    # Prepare edges and weights
    edges = []
    weights = []
    for w1, w2, w in edges_raw:
        edges.append((word_to_id[w1], word_to_id[w2]))
        weights.append(w)

    # Build the igraph.Graph using positional arguments to satisfy IDE type check:
    # Graph(n, edges, directed)
    g = ig.Graph(len(words_list), edges, False)
    
    # Store attributes directly
    g.vs["name"] = words_list
    g.es["weight"] = weights

    # Determine partition class and arguments for construction
    partition_kwargs = {}
    if partition_type.lower() == "modularity":
        if resolution_parameter is None or resolution_parameter == 1.0:
            partition_cls = la.ModularityVertexPartition
            res = 1.0
        else:
            partition_cls = la.RBConfigurationVertexPartition
            res = resolution_parameter
            partition_kwargs["resolution_parameter"] = res
    elif partition_type.lower() == "cpm":
        partition_cls = la.CPMVertexPartition
        res = 0.1 if resolution_parameter is None else resolution_parameter
        partition_kwargs["resolution_parameter"] = res
    else:
        logger.warning("Unsupported partition type: %s. Defaulting to 'modularity'.", partition_type)
        partition_cls = la.ModularityVertexPartition
        res = 1.0

    logger.info(
        "Running Leiden algorithm (partition=%s, resolution=%.4f, seed=%s)...",
        partition_type,
        res,
        seed,
    )

    # Run Leiden clustering. We check seed type to satisfy expected type inspection.
    try:
        if seed is not None:
            partition = la.find_partition(
                g,
                partition_cls,
                weights="weight",
                seed=seed,
                **partition_kwargs,
            )
        else:
            partition = la.find_partition(
                g,
                partition_cls,
                weights="weight",
                **partition_kwargs,
            )
    except Exception as exc:
        logger.exception("Failed to execute Leiden algorithm partitioning.")
        raise exc

    # Parse resulting partition into communities of words
    raw_communities = {}
    for vertex_idx, community_idx in enumerate(partition.membership):
        word = g.vs[vertex_idx]["name"]
        if community_idx not in raw_communities:
            raw_communities[community_idx] = []
        raw_communities[community_idx].append(word)

    # Sort words within communities, and filter by size
    communities = {}
    current_community_id = 0
    for comp_id in sorted(raw_communities.keys()):
        words_in_comp = sorted(raw_communities[comp_id])
        if len(words_in_comp) >= min_community_size:
            communities[current_community_id] = words_in_comp
            current_community_id += 1

    logger.info(
        "Leiden community detection complete. Detected %d communities (min_size=%d).",
        len(communities),
        min_community_size,
    )

    return communities
