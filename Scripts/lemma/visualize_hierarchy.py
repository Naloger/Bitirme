#!/usr/bin/env python3
"""Visualize the hierarchical taxonomy results from the database.

Queries the concepts table and displays them as a readable text-based tree
showing levels, labels, leader status, and PageRank scores. Supports automatic
ASCII fallback for Windows CP1254/non-UTF8 console environments.
"""

from __future__ import annotations

import argparse
from collections import defaultdict

# Add backend directory to Python path if running script directly
# sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlmodel import select

from Config.config import LEMMA_MATRIX_DATABASE_PATH, VISUALIZE_HIERARCHY_FORCE_ASCII
from backend.database.init_db import init_db
from backend.database.ORMSchemas.orm_schema_lemma_matrix import (
    LEMMA_MATRIX_METADATA,
    ConceptsModel,
)


def print_tree(
    node_id: int,
    prefix: str = "",
    is_last: bool = True,
    concept_map: dict[int, ConceptsModel] = None,
    children_map: dict[int, list[int]] = None,
    use_ascii: bool = False,
) -> None:
    """Recursively print concepts in a tree structure."""
    if concept_map is None or children_map is None:
        return

    node = concept_map[node_id]

    # Format node info
    leader_str = " [L]" if node.is_leader else ""
    pr_str = f", PR: {node.pagerank_score:.4f}" if node.pagerank_score is not None else ""
    vocab_str = f", Vocab ID: {node.vocab_id}" if node.vocab_id is not None else ""
    info = f"Level {node.level}: {node.label} (ID: {node.id}{pr_str}{leader_str}{vocab_str})"

    # Choose branch symbols
    if use_ascii:
        marker = "+-- " if is_last else "|-- "
        indent = "    " if is_last else "|   "
    else:
        marker = "└── " if is_last else "├── "
        indent = "    " if is_last else "│   "

    print(f"{prefix}{marker}{info}")

    # Calculate child prefix
    child_prefix = prefix + indent

    # Recurse children
    children = children_map.get(node_id, [])
    # Sort children so leaders are displayed first, then sorted by ID
    children.sort(key=lambda cid: (not (concept_map[cid].is_leader or False), cid))

    for i, child_id in enumerate(children):
        print_tree(
            child_id,
            prefix=child_prefix,
            is_last=(i == len(children) - 1),
            concept_map=concept_map,
            children_map=children_map,
            use_ascii=use_ascii,
        )


def visualize_database_hierarchy(db_path: str | None = None, force_ascii: bool | None = None) -> None:
    """Query the concepts table and print the hierarchical taxonomy tree."""
    target_force_ascii = force_ascii if force_ascii is not None else VISUALIZE_HIERARCHY_FORCE_ASCII
    target_db_path = db_path or LEMMA_MATRIX_DATABASE_PATH

    print(f"Connecting to database at: {target_db_path}")
    engine, session_factory = init_db(db_path=target_db_path, metadata=LEMMA_MATRIX_METADATA, echo=False)

    try:
        with session_factory() as session:
            concepts = session.exec(select(ConceptsModel)).all()

            if not concepts:
                print("\n[WARNING] The 'concepts' table is empty. Please run build_hierarchy.py first.")
                return

            # Maps for building tree
            concept_map: dict[int, ConceptsModel] = {}
            children_map: dict[int, list[int]] = defaultdict(list)
            level_counts: dict[int, int] = defaultdict(int)

            for c in concepts:
                if c.id is not None:
                    concept_map[c.id] = c
                    level_counts[c.level] += 1
                    if c.parent_id is not None:
                        children_map[c.parent_id].append(c.id)

            # Roots have parent_id == None
            roots = [cid for cid, c in concept_map.items() if c.parent_id is None]
            # Sort roots by level descending (highest level first) then by ID
            roots.sort(key=lambda cid: (-concept_map[cid].level, cid))

            print("\n======================================================================")
            print("                       Taxonomic Concept Hierarchy                    ")
            print("======================================================================")
            print(f"Total concepts found: {len(concepts)}")
            for lvl in sorted(level_counts.keys()):
                print(f"  Level {lvl}: {level_counts[lvl]} concepts")
            print(f"Trees (independent roots) found: {len(roots)}")
            print("======================================================================")

            try:
                if target_force_ascii:
                    raise UnicodeEncodeError("forced", "", 0, 1, "forced ascii option")
                for i, root_id in enumerate(roots):
                    print_tree(
                        root_id,
                        prefix="",
                        is_last=(i == len(roots) - 1),
                        concept_map=concept_map,
                        children_map=children_map,
                        use_ascii=False,
                    )
            except UnicodeEncodeError:
                # Fallback to plain ASCII characters for Windows console
                for i, root_id in enumerate(roots):
                    print_tree(
                        root_id,
                        prefix="",
                        is_last=(i == len(roots) - 1),
                        concept_map=concept_map,
                        children_map=children_map,
                        use_ascii=True,
                    )
            print("======================================================================\n")

    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize taxonomic concept hierarchy tree from DB.")
    parser.add_argument(
        "--db",
        "-d",
        type=str,
        default=None,
        help="Path to the SQLite database (defaults to the environment config path).",
    )
    parser.add_argument(
        "--ascii",
        "-a",
        action="store_true",
        default=VISUALIZE_HIERARCHY_FORCE_ASCII,
        help=f"Force using standard ASCII characters for output rendering (default: {VISUALIZE_HIERARCHY_FORCE_ASCII}).",
    )
    args = parser.parse_args()
    visualize_database_hierarchy(db_path=args.db, force_ascii=args.ascii)


if __name__ == "__main__":
    main()
