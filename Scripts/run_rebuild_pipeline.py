#!/usr/bin/env python3
"""End-to-end rebuild pipeline for taxonomic concept hierarchy.

Executes:
  1. PPMI table rebuild (clears PPMI and hierarchy tables, recalculates PPMI scores).
  2. Hierarchy rebuild (clears and populates concepts and concept connections).
  3. Visual tree display of the results.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add backend directory to Python path if running script directly
sys.path.append(str(Path(__file__).resolve().parent.parent))

from Scripts.build_hierarchy import build_taxonomy_hierarchy
from Scripts.build_ppmi_table import rebuild_ppmi_table
from Scripts.visualize_hierarchy import visualize_database_hierarchy
from Libs.Config.config import BUILD_HIERARCHY_MAX_LEVELS, BUILD_PPMI_THRESHOLD


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the end-to-end taxonomy rebuild pipeline.")
    parser.add_argument(
        "--db",
        "-d",
        type=str,
        default=None,
        help="Path to the SQLite database (defaults to the environment config path).",
    )
    parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=BUILD_PPMI_THRESHOLD,
        help=f"PPMI score threshold filter (default: {BUILD_PPMI_THRESHOLD}).",
    )
    parser.add_argument(
        "--max-levels",
        "-m",
        type=int,
        default=BUILD_HIERARCHY_MAX_LEVELS,
        help=f"Maximum levels for hierarchical taxonomy collapse (default: {BUILD_HIERARCHY_MAX_LEVELS}).",
    )
    parser.add_argument(
        "--no-visualize",
        "-nv",
        action="store_true",
        help="Skip printing the visual taxonomy tree at the end.",
    )
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("                STARTING TAXONOMY REBUILD PIPELINE               ")
    print("=" * 70)

    # Step 1: PPMI calculation
    print("\n--- STEP 1: Rebuilding PPMI Table ---")
    rebuild_ppmi_table(threshold=args.threshold, db_path=args.db)

    # Step 2: Hierarchical Leiden clustering
    print("\n--- STEP 2: Rebuilding Taxonomic Hierarchy ---")
    build_taxonomy_hierarchy(max_levels=args.max_levels, db_path=args.db)

    # Step 3: Hierarchy Tree visualization
    if not args.no_visualize:
        print("\n--- STEP 3: Visualizing Concept Hierarchy Tree ---")
        visualize_database_hierarchy(db_path=args.db)

    print("=" * 70)
    print("                PIPELINE EXECUTION COMPLETED                     ")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
