# -*- coding: utf-8 -*-
"""Script to seed keyword_db and memory_db with rich sample data for visualization."""

import os
import sys
from pathlib import Path

# Add project root to python path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from Scripts.infra.age.age_helpers import (
    get_age_connection,
    create_age_graph,
    drop_age_graph,
    execute_cypher_param
)
from Scripts.infra.age.rdf_quadstore import RDFQuadstore


def seed_keyword_graph() -> None:
    print("🌱 Seeding keyword_db / keyword_graph with sample NLP & Deep Learning words...")
    conn = get_age_connection("keyword_db")
    try:
        # Reset the graph
        drop_age_graph(conn, "keyword_graph")
        create_age_graph(conn, "keyword_graph")

        with conn.cursor() as cur:
            # 1. Define sample keywords (nodes)
            nodes = [
                {"id": 1, "word": "attention"},
                {"id": 2, "word": "transformer"},
                {"id": 3, "word": "llm"},
                {"id": 4, "word": "bert"},
                {"id": 5, "word": "gpt"},
                {"id": 6, "word": "embedding"},
                {"id": 7, "word": "vector"},
                {"id": 8, "word": "database"},
                {"id": 9, "word": "rag"},
                {"id": 10, "word": "retrieval"},
                {"id": 11, "word": "prompt"},
                {"id": 12, "word": "context"},
                {"id": 13, "word": "token"},
                {"id": 14, "word": "nlp"}
            ]

            # 2. Define sample co-occurrence weights (edges)
            edges = [
                {"v1": 1, "v2": 2, "w": 4.8},   # attention -> transformer
                {"v1": 2, "v2": 3, "w": 5.2},   # transformer -> llm
                {"v1": 2, "v2": 4, "w": 4.1},   # transformer -> bert
                {"v1": 3, "v2": 5, "w": 5.5},   # llm -> gpt
                {"v1": 3, "v2": 9, "w": 4.9},   # llm -> rag
                {"v1": 6, "v2": 7, "w": 4.6},   # embedding -> vector
                {"v1": 7, "v2": 8, "w": 4.3},   # vector -> database
                {"v1": 8, "v2": 9, "w": 4.7},   # database -> rag
                {"v1": 9, "v2": 10, "w": 5.0},  # rag -> retrieval
                {"v1": 10, "v2": 12, "w": 4.2}, # retrieval -> context
                {"v1": 11, "v2": 12, "w": 4.5}, # prompt -> context
                {"v1": 5, "v2": 11, "w": 4.4},  # gpt -> prompt
                {"v1": 3, "v2": 13, "w": 3.9},  # llm -> token
                {"v1": 14, "v2": 3, "w": 4.6},  # nlp -> llm
                {"v1": 14, "v2": 2, "w": 4.8}   # nlp -> transformer
            ]

            # 3. Insert Keyword nodes in batch
            execute_cypher_param(
                cur=cur,
                graph_name="keyword_graph",
                cypher_query=(
                    "UNWIND $batch AS item "
                    "CREATE (:Keyword {word: item.word, sqlite_id: item.id})"
                ),
                params_dict={"batch": nodes}
            )

            # 4. Insert CO_OCCUR_WITH edges
            execute_cypher_param(
                cur=cur,
                graph_name="keyword_graph",
                cypher_query=(
                    "UNWIND $batch AS edge "
                    "MATCH (a:Keyword {sqlite_id: edge.v1}) "
                    "MATCH (b:Keyword {sqlite_id: edge.v2}) "
                    "CREATE (a)-[:CO_OCCUR_WITH {weight: edge.w}]->(b)"
                ),
                params_dict={"batch": edges}
            )
            print(f"   ✅ Seeding keyword_graph complete: {len(nodes)} nodes, {len(edges)} edges inserted.")
    finally:
        conn.close()


def seed_rdf_quadstore() -> None:
    print("🌱 Seeding memory_db / rdf_quadstore_graph with sample Semantic Web data...")
    store = RDFQuadstore(db_name="memory_db", graph_name="rdf_quadstore_graph")
    store.clear()

    # Subjects
    s_python = {"type": "iri", "value": "http://example.org/resource/Python"}
    s_rag = {"type": "iri", "value": "http://example.org/resource/RAG"}
    s_transformers = {"type": "iri", "value": "http://example.org/resource/Transformers"}
    s_alice = {"type": "iri", "value": "http://example.org/user/alice"}
    s_bob = {"type": "iri", "value": "http://example.org/user/bob"}

    # Predicates
    p_type = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    p_label = "http://www.w3.org/2000/01/rdf-schema#label"
    p_created = "http://example.org/ontology/createdBy"
    p_uses = "http://example.org/ontology/usesLibrary"
    p_friend = "http://example.org/ontology/hasFriend"
    p_likes = "http://example.org/ontology/likesSubject"

    # Objects
    o_prog_lang = {"type": "iri", "value": "http://example.org/ontology/ProgrammingLanguage"}
    o_architecture = {"type": "iri", "value": "http://example.org/ontology/AIArchitecture"}
    o_library = {"type": "iri", "value": "http://example.org/ontology/SoftwareLibrary"}
    o_person = {"type": "iri", "value": "http://example.org/ontology/Person"}
    
    o_python_lbl = {"type": "literal", "value": "Python Language", "datatype": "http://www.w3.org/2001/XMLSchema#string", "lang": "en"}
    o_rag_lbl = {"type": "literal", "value": "Retrieval Augmented Generation", "datatype": "http://www.w3.org/2001/XMLSchema#string", "lang": "en"}
    o_trans_lbl = {"type": "literal", "value": "HuggingFace Transformers", "datatype": "http://www.w3.org/2001/XMLSchema#string", "lang": "en"}
    o_alice_lbl = {"type": "literal", "value": "Alice", "datatype": "http://www.w3.org/2001/XMLSchema#string", "lang": "en"}
    o_bob_lbl = {"type": "literal", "value": "Bob", "datatype": "http://www.w3.org/2001/XMLSchema#string", "lang": "en"}

    # Contexts
    c_meta = "http://example.org/context/metadata"
    c_users = "http://example.org/context/users"

    # Pushes to memory_db
    # Metadata Graph Quads
    store.add_quad(s_python, p_type, o_prog_lang, c_meta)
    store.add_quad(s_python, p_label, o_python_lbl, c_meta)
    
    store.add_quad(s_rag, p_type, o_architecture, c_meta)
    store.add_quad(s_rag, p_label, o_rag_lbl, c_meta)
    
    store.add_quad(s_transformers, p_type, o_library, c_meta)
    store.add_quad(s_transformers, p_label, o_trans_lbl, c_meta)

    store.add_quad(s_rag, p_uses, s_python, c_meta)
    store.add_quad(s_rag, p_uses, s_transformers, c_meta)

    # Users Graph Quads
    store.add_quad(s_alice, p_type, o_person, c_users)
    store.add_quad(s_alice, p_label, o_alice_lbl, c_users)
    store.add_quad(s_alice, p_likes, s_rag, c_users)
    store.add_quad(s_alice, p_likes, s_python, c_users)
    
    store.add_quad(s_bob, p_type, o_person, c_users)
    store.add_quad(s_bob, p_label, o_bob_lbl, c_users)
    store.add_quad(s_bob, p_likes, s_transformers, c_users)
    store.add_quad(s_bob, p_friend, s_alice, c_users)

    print(f"   ✅ Seeding rdf_quadstore complete: 16 semantic quads inserted.")


if __name__ == "__main__":
    seed_keyword_graph()
    seed_rdf_quadstore()
    print("\n🎉 Databases successfully seeded with interactive sample data!")
