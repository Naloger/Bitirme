#!/usr/bin/env python3
"""Interactive I/O test for Leiden Spreading Activation.

Run directly to input seed words and see the activated words listed.
Uses the real lemma_matrix.db database.

Usage:
    python Scripts/lemma/test_spreading_activation_io.py
    python Scripts/lemma/test_spreading_activation_io.py --seeds "sun,roman,god"
    python Scripts/lemma/test_spreading_activation_io.py --decay 0.9 --steps 8 --top-k 15
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add backend directory to Python path if running script directly
sys.path.append(str(Path(__file__).resolve().parent.parent))

from Config.config import LEMMA_MATRIX_DATABASE_PATH
from backend.database.init_db import init_db
from backend.database.ORMSchemas.orm_schema_lemma_matrix import LEMMA_MATRIX_METADATA
from Libs.Leiden.leiden_spreading_activation import spreading_activation


SEPARATOR = "=" * 70


def print_header(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def print_results(results: dict[str, float], seed_words: list[str]) -> None:
    """Pretty-print spreading activation results."""
    if not results:
        print("\n  (No words were activated. The database may be empty or seeds not found.)\n")
        return

    # Separate seeds from discovered words
    seed_set = set(w.lower().strip() for w in seed_words)
    seeds_in_results = {w: s for w, s in results.items() if w in seed_set}
    discovered = {w: s for w, s in results.items() if w not in seed_set}

    print(f"\n  Total activated words: {len(results)}")
    print(f"  Seeds found in graph: {len(seeds_in_results)}/{len(seed_words)}")
    print(f"  Discovered words:     {len(discovered)}")

    # Print seeds section
    if seeds_in_results:
        print(f"\n  {'─' * 50}")
        print(f"  SEED WORDS (input)")
        print(f"  {'─' * 50}")
        print(f"  {'Rank':<6} {'Word':<25} {'Activation Score':<15}")
        print(f"  {'─' * 50}")
        for rank, (word, score) in enumerate(seeds_in_results.items(), 1):
            bar = "█" * min(int(score * 20), 40)
            print(f"  {rank:<6} {word:<25} {score:<15.6f} {bar}")

    # Print discovered words section
    if discovered:
        print(f"\n  {'─' * 50}")
        print(f"  DISCOVERED WORDS (output)")
        print(f"  {'─' * 50}")
        print(f"  {'Rank':<6} {'Word':<25} {'Activation Score':<15}")
        print(f"  {'─' * 50}")

        # Find max score for bar scaling
        max_score = max(discovered.values()) if discovered else 1.0

        for rank, (word, score) in enumerate(discovered.items(), 1):
            normalized = score / max_score if max_score > 0 else 0
            bar = "█" * max(1, int(normalized * 30))
            print(f"  {rank:<6} {word:<25} {score:<15.6f} {bar}")

    print()


def run_interactive(session, args) -> None:
    """Interactive loop: prompt for seed words, display activated words."""
    print_header("LEIDEN SPREADING ACTIVATION — Interactive Test")
    print(f"  Database: {LEMMA_MATRIX_DATABASE_PATH}")
    print(f"  Decay: {args.decay}  |  Steps: {args.steps}  |  Threshold: {args.threshold}")
    print(f"  Intra-boost: {args.intra_boost}  |  Inter-penalty: {args.inter_penalty}")
    if args.top_k:
        print(f"  Top-K: {args.top_k}")
    print(f"\n  Type seed words separated by commas, or 'quit' to exit.\n")

    while True:
        try:
            raw_input = input("  Enter seed words > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Exiting.")
            break

        if not raw_input or raw_input.lower() in ("quit", "exit", "q"):
            print("  Goodbye!")
            break

        seed_words = [w.strip() for w in raw_input.split(",") if w.strip()]
        if not seed_words:
            print("  Please enter at least one word.\n")
            continue

        print(f"\n  Activating seeds: {seed_words}")
        print(f"  {'·' * 40}")

        results = spreading_activation(
            session=session,
            seed_words=seed_words,
            decay=args.decay,
            firing_threshold=args.threshold,
            max_steps=args.steps,
            intra_community_boost=args.intra_boost,
            inter_community_penalty=args.inter_penalty,
            initial_activation=1.0,
            top_k=args.top_k,
        )

        print_results(results, seed_words)


def run_single(session, args, seed_words: list[str]) -> None:
    """Single-shot mode: run once with provided seeds and exit."""
    print_header("LEIDEN SPREADING ACTIVATION — Single Run")
    print(f"  Database: {LEMMA_MATRIX_DATABASE_PATH}")
    print(f"  Seeds:    {seed_words}")
    print(f"  Decay: {args.decay}  |  Steps: {args.steps}  |  Threshold: {args.threshold}")
    print(f"  Intra-boost: {args.intra_boost}  |  Inter-penalty: {args.inter_penalty}")
    if args.top_k:
        print(f"  Top-K: {args.top_k}")

    results = spreading_activation(
        session=session,
        seed_words=seed_words,
        decay=args.decay,
        firing_threshold=args.threshold,
        max_steps=args.steps,
        intra_community_boost=args.intra_boost,
        inter_community_penalty=args.inter_penalty,
        initial_activation=1.0,
        top_k=args.top_k,
    )

    print_results(results, seed_words)

    # Also print a simple INPUT → OUTPUT summary
    print_header("SUMMARY: INPUT → OUTPUT")
    print(f"\n  INPUT  (seed words):     {', '.join(seed_words)}")
    discovered = [w for w in results if w.lower().strip() not in set(s.lower().strip() for s in seed_words)]
    print(f"  OUTPUT (activated words): {', '.join(discovered) if discovered else '(none)'}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactive I/O test for Leiden Spreading Activation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--seeds", "-s",
        type=str,
        default=None,
        help="Comma-separated seed words for single-shot mode. If omitted, runs interactively.",
    )
    parser.add_argument(
        "--decay", "-d",
        type=float,
        default=0.8,
        help="Decay factor per hop (0 < decay ≤ 1).",
    )
    parser.add_argument(
        "--steps", "-m",
        type=int,
        default=5,
        help="Maximum propagation steps.",
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.01,
        help="Minimum activation to continue spreading.",
    )
    parser.add_argument(
        "--intra-boost",
        type=float,
        default=1.0,
        help="Multiplier for edges within the same Leiden community.",
    )
    parser.add_argument(
        "--inter-penalty",
        type=float,
        default=0.3,
        help="Multiplier for edges crossing community boundaries.",
    )
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=None,
        help="Return only the top-K activated words.",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Path to SQLite database (defaults to config path).",
    )
    args = parser.parse_args()

    db_path = args.db or LEMMA_MATRIX_DATABASE_PATH
    print(f"\n  Connecting to database: {db_path}")
    engine, session_factory = init_db(db_path=db_path, metadata=LEMMA_MATRIX_METADATA, echo=False)

    try:
        with session_factory() as session:
            if args.seeds:
                seed_words = [w.strip() for w in args.seeds.split(",") if w.strip()]
                run_single(session, args, seed_words)
            else:
                run_interactive(session, args)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
