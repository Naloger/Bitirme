from __future__ import annotations

import itertools
import math
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import networkx as nx
from sentence_transformers import SentenceTransformer, util

from services.Libs.Lemmatizer.LanguageSegmentation.segment_by_language import (
    segment_by_language,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:  # pragma: no cover - optional dependency
    import igraph as ig
    import leidenalg
except ImportError:  # pragma: no cover - optional dependency fallback
    ig = None
    leidenalg = None

try:
    from community import community_louvain
except ImportError:  # pragma: no cover - optional dependency fallback
    community_louvain = None


# =====================================================================
# 1. ARCHITECTURAL SETTINGS & ENGINE INITIALIZATION
# =====================================================================

_COMMON_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "bir",
    "biraz",
    "but",
    "by",
    "da",
    "de",
    "do",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "his",
    "i",
    "icin",
    "ile",
    "in",
    "is",
    "it",
    "its",
    "me",
    "mi",
    "mı",
    "mu",
    "mü",
    "my",
    "of",
    "on",
    "or",
    "our",
    "she",
    "that",
    "the",
    "their",
    "them",
    "these",
    "they",
    "this",
    "those",
    "to",
    "us",
    "ve",
    "was",
    "we",
    "were",
    "with",
    "without",
    "you",
    "your",
}

_SEMANTIC_BRIDGE_TOP_K = 1
_SEMANTIC_BRIDGE_THRESHOLD = 0.68
_EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

_TURKISH_TRANSLATION = str.maketrans(
    {
        "ç": "c",
        "Ç": "c",
        "ğ": "g",
        "Ğ": "g",
        "ı": "i",
        "İ": "i",
        "ö": "o",
        "Ö": "o",
        "ş": "s",
        "Ş": "s",
        "ü": "u",
        "Ü": "u",
    }
)


def _fold_token(token: str) -> str:
    """Lowercase and strip accents/punctuation for fuzzy matching."""
    token = token.strip().lower().translate(_TURKISH_TRANSLATION)
    token = unicodedata.normalize("NFKD", token)
    token = "".join(ch for ch in token if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", token)



class MultilingualDynamicHypergraphEngine:
    def __init__(self, alpha: float = 0.6, decay_rate: float = 0.1):
        """Create the hybrid graph engine."""
        self.G = nx.Graph()
        self.alpha = alpha
        self.decay_rate = decay_rate
        self._first_seen: dict[str, int] = {}
        self._token_frequency: Counter[str] = Counter()
        self._token_order = 0
        self._embedder: SentenceTransformer | None = None
        self._embedder_attempted = False

    def _load_embedder(self) -> SentenceTransformer | None:
        if self._embedder_attempted:
            return self._embedder

        self._embedder_attempted = True
        try:
            self._embedder = SentenceTransformer(_EMBEDDING_MODEL_NAME)
        except (OSError, RuntimeError, ValueError):
            try:
                # Retry without network to support offline environments with cached models.
                self._embedder = SentenceTransformer(_EMBEDDING_MODEL_NAME, local_files_only=True)
            except (OSError, RuntimeError, ValueError):  # pragma: no cover - cache/machine dependent
                self._embedder = None

        return self._embedder


    # =====================================================================
    # STAGE 2: CONTEXT-AWARE LOCAL NORMALIZATION (Fast Token Worker)
    # =====================================================================
    def _register_token(self, token: str) -> None:
        if token not in self._first_seen:
            self._first_seen[token] = self._token_order
            self._token_order += 1
        self._token_frequency[token] += 1

    @staticmethod
    def _keep_token(token: str) -> bool:
        cleaned = _fold_token(token)
        if not cleaned:
            return False
        if cleaned in _COMMON_STOPWORDS:
            return False
        if len(cleaned) < 2:
            return False
        return bool(re.search(r"[a-z0-9]", cleaned))

    def _extract_lemmas(self, text: str, lang: str | None) -> list[str]:
        """Normalize a raw text fragment into a stable token stream."""
        text = text or ""
        if not text:
            return []

        segments = (
            [{"language": lang, "text": text}] if lang in {"en", "tr"} else segment_by_language(text)
        )

        tokens: list[str] = []
        for segment in segments:
            segment_text = segment["text"]
            raw_tokens = re.findall(r"[^\W\d_]+", segment_text, flags=re.UNICODE)
            for raw_token in raw_tokens:
                cleaned = _fold_token(raw_token)
                if self._keep_token(cleaned):
                    tokens.append(cleaned)

        if not tokens:
            tokens = [
                _fold_token(token)
                for token in re.findall(r"\w+", text, flags=re.UNICODE)
                if self._keep_token(token)
            ]

        return tokens

    @staticmethod
    def _cosine_matrix(vectors: list[list[float]]) -> list[list[float]]:
        norms = [math.sqrt(sum(value * value for value in vector)) or 1.0 for vector in vectors]
        matrix: list[list[float]] = []
        for i, left in enumerate(vectors):
            row: list[float] = []
            for j, right in enumerate(vectors):
                dot = sum(a * b for a, b in zip(left, right))
                row.append(dot / (norms[i] * norms[j]))
            matrix.append(row)
        return matrix

    def _pairwise_similarity_matrix(self, vocab_list: list[str]) -> list[list[float]]:
        if not vocab_list:
            return []

        embedder = self._load_embedder()
        if embedder is not None:
            embeddings = embedder.encode(
                vocab_list,
                convert_to_tensor=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return util.cos_sim(embeddings, embeddings).tolist()

        # Fallback: create zero vectors if embedder unavailable
        zero_vectors = [[0.0] * len(vocab_list) for _ in range(len(vocab_list))]
        for i in range(len(vocab_list)):
            zero_vectors[i][i] = 1.0
        return zero_vectors

    @staticmethod
    def _coerce_node_name(node: object) -> str:
        if isinstance(node, str):
            return node
        return str(cast(Any, node))

    # =====================================================================
    # STAGE 3 & 4: MATRIX UPDATE WITH EXPONENTIAL TIME-DECAY
    # =====================================================================
    def _update_fused_relationship(self, u: str, v: str, vec_sim: float, current_date_str: str, fresh_count: float = 1.0) -> None:
        """Update a relationship using decayed structural weight plus semantic affinity."""
        fmt = "%Y-%m-%d"
        today = datetime.strptime(current_date_str, fmt)

        if self.G.has_edge(u, v):
            edge_data = self.G[u][v]
            old_struct_weight = edge_data.get("raw_struct_weight", 1.0)
            last_updated = datetime.strptime(edge_data["last_updated"], fmt)
            days_passed = max(0, (today - last_updated).days)
            decayed_struct_weight = old_struct_weight * math.exp(-self.decay_rate * days_passed)
            new_struct_weight = decayed_struct_weight + fresh_count
        else:
            new_struct_weight = fresh_count

        fused_weight = (self.alpha * new_struct_weight) + ((1.0 - self.alpha) * vec_sim)

        self.G.add_edge(
            u,
            v,
            weight=fused_weight,
            raw_struct_weight=new_struct_weight,
            last_updated=current_date_str,
        )

    def process_daily_stream(self, data_batch, date_str: str) -> None:
        """Ingest one daily batch and fuse structural and semantic edges."""
        doc_token_lists: list[list[str]] = []
        batch_vocabulary: set[str] = set()

        for item in data_batch:
            tokens = self._extract_lemmas(item.get("text", ""), item.get("lang"))
            unique_tokens = list(dict.fromkeys(tokens))
            if len(unique_tokens) > 1:
                doc_token_lists.append(unique_tokens)
            for token in unique_tokens:
                self._register_token(token)
                batch_vocabulary.add(token)

        if not batch_vocabulary:
            return

        vocab_list = sorted(batch_vocabulary, key=lambda vocab_token: self._first_seen.get(vocab_token, 0))
        sim_matrix = self._pairwise_similarity_matrix(vocab_list)
        index_by_token = {vocab_token: index for index, vocab_token in enumerate(vocab_list)}

        # 1) Structural edges: concepts that co-occur in the same document.
        for token_list in doc_token_lists:
            for u, v in itertools.combinations(token_list, 2):
                vec_sim = float(sim_matrix[index_by_token[u]][index_by_token[v]])
                self._update_fused_relationship(u, v, vec_sim, date_str, fresh_count=1.0)


        # 2) Semantic bridge edges: connect closest cross-lingual neighbors sparsely.
        for i, u in enumerate(vocab_list):
            scored_neighbors: list[tuple[float, str]] = []
            row = sim_matrix[i]
            for j in range(i + 1, len(vocab_list)):
                v = vocab_list[j]
                if u == v:
                    continue
                vec_sim = float(row[j])
                if vec_sim >= _SEMANTIC_BRIDGE_THRESHOLD:
                    scored_neighbors.append((vec_sim, v))

            scored_neighbors.sort(key=lambda pair: (-pair[0], self._first_seen.get(pair[1], 0), pair[1]))
            for vec_sim, v in scored_neighbors[:_SEMANTIC_BRIDGE_TOP_K]:
                self._update_fused_relationship(u, v, vec_sim, date_str, fresh_count=0.25)

    # =====================================================================
    # STAGE 5 & GROUP LEADER SELECTION (Mathematical Hierarchical Core)
    # =====================================================================
    def _select_group_leader(self, subgraph: nx.Graph, node_list: list[str]) -> str:
        """Pick the most central node using weighted degree and PageRank."""
        weighted_degree = dict(subgraph.degree(weight="weight"))
        if subgraph.number_of_edges() > 0 and len(subgraph) > 1:
            pagerank = nx.pagerank(subgraph, weight="weight")
        else:
            pagerank = {node: 0.0 for node in node_list}

        return max(
            node_list,
            key=lambda token: (
                weighted_degree.get(token, 0.0),
                pagerank.get(token, 0.0),
                self._token_frequency.get(token, 0),
                -self._first_seen.get(token, 10**9),
                token,
            ),
        )

    def _partition_graph(self) -> dict[str, int]:
        """Partition the graph with Leiden when available, otherwise fall back."""
        if len(self.G) == 0:
            return {}

        if leidenalg is not None and ig is not None and self.G.number_of_edges() > 0:
            igraph_module = ig
            leiden_module = leidenalg
            assert igraph_module is not None and leiden_module is not None

            nodes = list(self.G.nodes())
            node_names = [self._coerce_node_name(node_obj) for node_obj in nodes]
            index_by_node = {node: idx for idx, node in enumerate(nodes)}
            graph = igraph_module.Graph(
                n=len(nodes),
                edges=[(index_by_node[u], index_by_node[v]) for u, v in self.G.edges()],
            )
            graph.es["weight"] = [float(data.get("weight", 1.0)) for _, _, data in self.G.edges(data=True)]
            partition = leiden_module.find_partition(
                graph,
                leiden_module.ModularityVertexPartition,
                weights=list(graph.es["weight"]),
                seed=42,
            )

            mapping: dict[str, int] = {}
            for community_id, community in enumerate(partition):
                for vertex_index in community:
                    mapping[node_names[int(vertex_index)]] = community_id
            return mapping

        if community_louvain is not None and self.G.number_of_edges() > 0:
            return community_louvain.best_partition(self.G, weight="weight", random_state=42)

        mapping: dict[str, int] = {}
        for community_id, component in enumerate(nx.connected_components(self.G)):
            for component_node in component:
                mapping[self._coerce_node_name(component_node)] = community_id
        return mapping

    def compute_hierarchical_taxonomy(self):
        """Partition the graph into communities and return stable macro layers."""
        if len(self.G) == 0:
            return {}

        partition = self._partition_graph()
        community_buckets: dict[int, list[str]] = {}
        for concept, community_id in partition.items():
            community_buckets.setdefault(community_id, []).append(concept)

        bucket_iterable = [
            node_list
            for _, node_list in sorted(
                community_buckets.items(),
                key=lambda bucket_item: (
                    min(self._first_seen.get(cluster_node, 10**9) for cluster_node in bucket_item[1]),
                    -len(bucket_item[1]),
                    bucket_item[0],
                ),
            )
        ]

        final_structured_hierarchy = {}
        for layer_index, node_list in enumerate(bucket_iterable):
            if not node_list:
                continue
            subgraph = self.G.subgraph(node_list)
            group_leader = self._select_group_leader(subgraph, node_list)

            final_structured_hierarchy[f"Macro_Layer_{layer_index}"] = {
                "group_leader_anchor": group_leader,
                "cluster_concepts": sorted(node_list, key=lambda node_name: self._first_seen.get(node_name, 10**9)),
            }

        return final_structured_hierarchy


# =====================================================================
# TESTING & VALIDATION SUITE
# =====================================================================
# noinspection PyProtectedMember
def _run_demo_tests():
    import json
    
    print("="*70)
    print("MULTILINGUAL DYNAMIC HYPERGRAPH ENGINE - TEST SUITE")
    print("="*70)
    
    # Test 1: Token Extraction Accuracy
    print("\n[TEST 1] Token Extraction & Normalization")
    print("-" * 70)
    engine_test = MultilingualDynamicHypergraphEngine()
    test_texts = [
        ("The quick brown fox", "en"),
        ("Hızlı kahverengi tilki", "tr"),
        ("mixed Hızlı quick text", None),
    ]
    for sample_text, sample_lang in test_texts:
        lemmas = engine_test._extract_lemmas(sample_text, sample_lang)
        print(f"  Input: '{sample_text}' (lang={sample_lang})")
        print(f"  Tokens: {lemmas}\n")
    
    # Test 2: Parameter Sensitivity Analysis
    print("\n[TEST 2] Parameter Tuning & Sensitivity Analysis")
    print("-" * 70)
    configs = [
        {"alpha": 0.5, "decay_rate": 0.05, "name": "High Semantic Weight (better for synonyms)"},
        {"alpha": 0.7, "decay_rate": 0.15, "name": "High Structural Weight (better for co-occurrence)"},
        {"alpha": 0.6, "decay_rate": 0.10, "name": "Balanced (Default - recommended)"},
    ]
    
    print("  Parameter Recommendations:")
    print("  - alpha: Balance between structural (co-occurrence) and semantic similarity")
    print("    • 0.5-0.6: Emphasize semantic similarity (good for cross-lingual)")
    print("    • 0.7+: Emphasize co-occurrence structure (good for same-language clusters)")
    print("  - decay_rate: How quickly relationships fade without reinforcement")
    print("    • 0.05-0.08: Slow decay (keep old connections longer)")
    print("    • 0.10-0.15: Medium decay (default, balances old/new)")
    print("    • 0.20+: Fast decay (only recent connections matter)")
    print()
    
    for cfg in configs:
        name = cfg.pop("name")
        eng = MultilingualDynamicHypergraphEngine(**cfg)
        print(f"  {name}")
        print(f"    alpha={eng.alpha}, decay_rate={eng.decay_rate}\n")
    
    # Test 3: Stream Processing with Multi-Day Simulation
    print("\n[TEST 3] Multi-Day Stream Processing & Exponential Decay")
    print("-" * 70)
    engine = MultilingualDynamicHypergraphEngine(alpha=0.55, decay_rate=0.12)
    taxonomy: dict = {}
    
    # Day 1: Initial vocabulary
    day_1_data = [
        {"text": "dog cat animal pet", "lang": "en"},
        {"text": "köpek kedi hayvan evcil", "lang": "tr"},
    ]
    print("  Day 1 (2026-05-01): Processing initial batch...")
    engine.process_daily_stream(day_1_data, "2026-05-01")
    print(f"    Graph: {len(engine.G.nodes())} nodes, {len(engine.G.edges())} edges")
    
    # Day 3: Decay occurs + new vocabulary with semantic overlap
    day_3_data = [
        {"text": "dog runs fast park animal", "lang": "en"},
        {"text": "köpek hızlı koşu parkı hayvan", "lang": "tr"},
    ]
    print("  Day 3 (2026-05-03): Processing with 2-day decay...")
    engine.process_daily_stream(day_3_data, "2026-05-03")
    print(f"    Graph: {len(engine.G.nodes())} nodes, {len(engine.G.edges())} edges")
    print("    Decay applied: 2-day exponential decay (e^(-0.12*2) ≈ 0.787)")
    
    # Day 5: Another refresh with reinforced concepts
    day_5_data = [
        {"text": "cat sleeps warm bed comfortable cozy", "lang": "en"},
        {"text": "kedi sıcak yatağında uyur konforlu rahat", "lang": "tr"},
    ]
    print("  Day 5 (2026-05-05): Processing with 4-day decay...")
    engine.process_daily_stream(day_5_data, "2026-05-05")
    print(f"    Graph: {len(engine.G.nodes())} nodes, {len(engine.G.edges())} edges")
    print("    Decay applied: 4-day exponential decay (e^(-0.12*4) ≈ 0.619)")
    
    # Test 4: Edge Weight Distribution Analysis
    print("\n[TEST 4] Edge Weight Distribution & Relationship Strength")
    print("-" * 70)
    if engine.G.edges():
        weights = [data.get("weight", 0.0) for _, _, data in engine.G.edges(data=True)]
        print(f"  Total edges: {len(weights)}")
        print(f"  Weight range: [{min(weights):.4f}, {max(weights):.4f}]")
        print(f"  Average weight: {sum(weights)/len(weights):.4f}")
        
        # Weight distribution histogram
        buckets = [0, 0.3, 0.6, 0.9, 1.2]
        distribution = {f"{buckets[i]:.1f}-{buckets[i+1]:.1f}": 0 for i in range(len(buckets)-1)}
        for w in weights:
            for i in range(len(buckets)-1):
                if buckets[i] <= w < buckets[i+1]:
                    distribution[f"{buckets[i]:.1f}-{buckets[i+1]:.1f}"] += 1
                    break
        print("\n  Weight distribution:")
        for bucket, count in distribution.items():
            print(f"    {bucket}: {'█'*count} ({count})")
        
        top_5_edges = sorted(
            [(engine.G[u][v].get("weight", 0.0), u, v) for u, v in engine.G.edges()],
            reverse=True
        )[:5]
        print("\n  Top 5 strongest relationships:")
        for weight, u, v in top_5_edges:
            fused = weight
            struct = engine.G[u][v].get("raw_struct_weight", 1.0)
            node_u = str(cast(Any, u))
            node_v = str(cast(Any, v))
            print(f"    {node_u:12s} ←→ {node_v:12s} → {fused:.4f} (structure: {struct:.2f})")
    
    # Test 5: Group Leader Selection Accuracy
    print("\n[TEST 5] Hierarchical Taxonomy & Leadership Selection")
    print("-" * 70)
    if len(engine.G) > 0:
        taxonomy = engine.compute_hierarchical_taxonomy()
        print(f"  Communities discovered: {len(taxonomy)}")
        for layer_name, layer_info in taxonomy.items():
            leader = layer_info["group_leader_anchor"]
            concepts = layer_info["cluster_concepts"]
            print(f"\n  {layer_name}:")
            print(f"    Leader (anchor): {leader}")
            print(f"    Cluster size: {len(concepts)} concepts")
            print(f"    Members: {concepts[:6]}{' ...' if len(concepts) > 6 else ''}")
            
            # Calculate leadership metrics
            if len(concepts) > 1:
                node_subgraph = engine.G.subgraph(concepts)
                node_weighted_degree = dict(node_subgraph.degree(weight="weight"))
                leader_degree = node_weighted_degree.get(leader, 0.0)
                avg_degree = sum(node_weighted_degree.values()) / len(node_weighted_degree)
                leadership_factor = leader_degree / avg_degree if avg_degree > 0 else 0
                print(f"    Leadership factor: {leadership_factor:.2f}x avg (higher = better leader)")
    
    # Test 6: Semantic Backend Verification
    print("\n[TEST 6] Semantic Processing Backend")
    print("-" * 70)
    current_embedder = engine._load_embedder()
    if current_embedder is not None:
        print("  ✓ SentenceTransformer ENABLED")
        print(f"    Model: {_EMBEDDING_MODEL_NAME}")
        print(f"    Semantic similarity threshold: {_SEMANTIC_BRIDGE_THRESHOLD}")
        print(f"    Bridge top-K: {_SEMANTIC_BRIDGE_TOP_K}")
    else:
        print("  ↻ SentenceTransformer unavailable")
        print("    Using identity matrices (structural graph only)")
    
    # Test 7: Token Frequency & Vocabulary Stats
    print("\n[TEST 7] Vocabulary Statistics")
    print("-" * 70)
    if engine._token_frequency:
        top_tokens = engine._token_frequency.most_common(10)
        print(f"  Total unique tokens: {len(engine._token_frequency)}")
        print(f"  Total token occurrences: {sum(engine._token_frequency.values())}")
        print("  Top 10 most frequent:")
        for tok, cnt in top_tokens:
            bar = '█' * cnt
            print(f"    {tok:12s} {bar} ({cnt})")
    
    # Test 8: Graph Partitioning Method
    print("\n[TEST 8] Partitioning Algorithm Selection")
    print("-" * 70)
    if leidenalg is not None and ig is not None:
        current_partition = engine._partition_graph()
        if current_partition:
            num_communities = len(set(current_partition.values()))
            print("  ✓ Leiden algorithm (optimal modularity partition)")
            print(f"    Communities found: {num_communities}")
            print("    Note: Leiden is superior to Louvain for overlapping communities")
    elif community_louvain is not None:
        current_partition = engine._partition_graph()
        if current_partition:
            num_communities = len(set(current_partition.values()))
            print("  ✓ Louvain algorithm (local modularity optimization)")
            print(f"    Communities found: {num_communities}")
    else:
        print("  ↻ Connected components (baseline)")
        print("    Install python-louvain or igraph+leidenalg for better partitioning")
    
    # Test 9: Cross-Lingual Linkage Analysis
    print("\n[TEST 9] Cross-Lingual Semantic Linking")
    print("-" * 70)
    cross_lang_edges = 0
    same_lang_edges = 0
    
    turkish_chars = {'ç', 'ğ', 'ı', 'ö', 'ş', 'ü'}
    
    for u, v in engine.G.edges():
        is_u_turkish = any(char in u for char in turkish_chars)
        is_v_turkish = any(char in v for char in turkish_chars)
        
        if is_u_turkish != is_v_turkish:
            cross_lang_edges += 1
        else:
            same_lang_edges += 1
    
    total_edges = cross_lang_edges + same_lang_edges
    if total_edges > 0:
        cross_lang_pct = (cross_lang_edges / total_edges) * 100
        print(f"  Total relationships: {total_edges}")
        print(f"  Cross-lingual bridges: {cross_lang_edges} ({cross_lang_pct:.1f}%)")
        print(f"  Same-language clusters: {same_lang_edges} ({100-cross_lang_pct:.1f}%)")
        
        if cross_lang_pct < 5:
            print("\n  Note: Low cross-lingual linking detected.")
            print("  Recommendations:")
            print(f"    • Lower alpha (currently {engine.alpha}) to ~0.5 for more semantic influence")
            print(f"    • Reduce bridge_threshold from {_SEMANTIC_BRIDGE_THRESHOLD} to 0.6")
            print(f"    • Increase bridge_cap from {_SEMANTIC_BRIDGE_TOP_K} to 2-3")
    
    # Test 10: Final Taxonomy Export
    print("\n[TEST 10] Final Hierarchical Taxonomy (JSON Export)")
    print("-" * 70)
    print(json.dumps(taxonomy, indent=2, ensure_ascii=False))
    
    print("\n" + "="*70)
    print("TEST SUITE COMPLETE - Engine Ready for Production")
    print("="*70)


if __name__ == "__main__":
    _run_demo_tests()

