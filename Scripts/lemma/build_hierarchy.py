"""Build hierarchical communities recursively using Leiden and PageRank.

Level 0 is initialized from vocabulary entries present in the PPMI lemma matrix.
Subsequent levels are collapsed using the concept_connections of the previous level.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

# Add backend directory to Python path if running script directly
sys.path.append(str(Path(__file__).resolve().parent.parent))

import igraph as ig
import leidenalg as la
from sqlmodel import  select, delete

from Libs.Config.config import LEMMA_MATRIX_DATABASE_PATH, BUILD_HIERARCHY_MAX_LEVELS
from backend.database.init_db import init_db
from backend.database.ORMSchemas.orm_schema_lemma_matrix import (
	LEMMA_MATRIX_METADATA,
	VocabularyModel,
	PPMILemmaMatrixModel,
	ConceptsModel,
	ConceptConnectionsModel,
)


def _find_leader_and_scores(
	nodes_in_comm: list[int],
	comm_edges: list[tuple[int, int, float]]
) -> tuple[int, dict[int, float]]:
	"""Calculate local PageRank of nodes in a community and return (leader_concept_id, dict_of_scores)."""
	if len(nodes_in_comm) == 1:
		node = nodes_in_comm[0]
		return node, {node: 1.0}

	if not comm_edges:
		# Fallback if no edges in the community: assign equal scores and return first node as leader
		score = 1.0 / len(nodes_in_comm)
		return nodes_in_comm[0], {node: score for node in nodes_in_comm}

	# Create a mapping from concept ID to local index
	local_nodes = list(sorted(nodes_in_comm))
	node_to_idx = {n: idx for idx, n in enumerate(local_nodes)}

	# Build the subgraph
	igraph_edges = [(node_to_idx[n1], node_to_idx[n2]) for n1, n2, _ in comm_edges]
	igraph_weights = [w for _, _, w in comm_edges]

	g = ig.Graph(len(local_nodes), igraph_edges, directed=False)
	cast(Any, g).es["weight"] = igraph_weights

	# Calculate PageRank
	try:
		scores = cast(Any, g).pagerank(weights="weight")
	except Exception:  # noqa: PyBroadException
		# Fallback to unweighted PageRank if weighted fails
		try:
			scores = cast(Any, g).pagerank()
		except Exception:  # noqa: PyBroadException
			# Fallback to degree centrality if PageRank fails
			degrees = cast(Any, g).degree()
			total_deg = float(cast(Any, sum(degrees)) or 1.0)
			scores = [d / total_deg for d in degrees]

	# Map back to concept IDs
	node_scores = {local_nodes[idx]: score for idx, score in enumerate(scores)}

	# Find leader
	leader = max(node_scores.keys(), key=lambda n: node_scores[n])
	return leader, node_scores


def build_taxonomy_hierarchy(max_levels: int | None = None, db_path: str | None = None) -> None:
	"""Rebuild concepts and concept_connections recursively by clustering connections."""
	target_max_levels = max_levels if max_levels is not None else BUILD_HIERARCHY_MAX_LEVELS
	target_db_path = db_path or LEMMA_MATRIX_DATABASE_PATH

	print(f"Connecting to database at: {target_db_path}")
	engine, session_factory = init_db(db_path=target_db_path, metadata=LEMMA_MATRIX_METADATA, echo=False)

	try:
		with session_factory() as session:
			# Clear existing hierarchy tables
			print("Clearing concepts and concept_connections tables...")
			session.exec(delete(ConceptConnectionsModel))
			session.exec(delete(ConceptsModel))
			session.commit()

			# 1. Initialize Level 0 (Base vocabulary words present in PPMI matrix)
			print("Initializing Level 0 base concepts from vocabulary in PPMI matrix...")
			
			# Get unique vocabulary IDs in PPMI table
			ppmi_edges = session.exec(select(PPMILemmaMatrixModel)).all()
			
			raw_vocab_ids = set()
			for edge in ppmi_edges:
				raw_vocab_ids.add(edge.vocab1_id)
				raw_vocab_ids.add(edge.vocab2_id)

			if not raw_vocab_ids:
				print("No connections found in ppmi_lemma_matrix. Cannot build hierarchy.")
				return

			# Retrieve vocabulary entries to get labels
			vocab_records = session.exec(
				select(VocabularyModel).where(cast(Any, VocabularyModel.id).in_(list(raw_vocab_ids)))
			).all()
			
			vocab_map = {v.id: v for v in vocab_records if v.id is not None}
			valid_vocab_ids = set(vocab_map.keys())

			# Filter ppmi_edges to only include valid pairs (where both vocabulary words exist)
			ppmi_edges = [
				edge for edge in ppmi_edges
				if edge.vocab1_id in valid_vocab_ids and edge.vocab2_id in valid_vocab_ids
			]

			# Insert Level 0 Concepts
			print(f"Inserting {len(valid_vocab_ids)} concepts at Level 0...")
			level_0_concepts: list[ConceptsModel] = []
			for v_id in sorted(valid_vocab_ids):
				vocab_item = vocab_map[v_id]
				level_0_concepts.append(
					ConceptsModel(
						level=0,
						parent_id=None,
						vocab_id=v_id,
						label=vocab_item.word,
						pagerank_score=1.0,
						is_leader=True
					)
				)
			
			session.add_all(level_0_concepts)
			session.commit()
			
			# Create map of vocab_id -> concept_id for Level 0
			vocab_id_to_concept_id = {c.vocab_id: c.id for c in level_0_concepts if c.vocab_id is not None and c.id is not None}

			current_level = 0
			concept_id_sequence = max(cast(list[int], [c.id for c in level_0_concepts if c.id is not None])) + 1
			concept_conn_id_sequence = 1

			while current_level < target_max_levels:
				print(f"\n======================================")
				print(f"Starting Clustering Level {current_level} -> {current_level + 1}")
				print(f"======================================")

				# Gather concepts at current level
				current_concepts = session.exec(
					select(ConceptsModel).where(ConceptsModel.level == current_level)
				).all()

				if not current_concepts:
					print(f"No concepts found at level {current_level}. Hierarchy complete.")
					break

				concept_ids = [c.id for c in current_concepts if c.id is not None]
				concept_map = {c.id: c for c in current_concepts if c.id is not None}

				# Gather edges
				edges_list: list[tuple[int, int, float]] = []

				if current_level == 0:
					# Read from ppmi_lemma_matrix
					for edge in ppmi_edges:
						c1 = vocab_id_to_concept_id.get(edge.vocab1_id)
						c2 = vocab_id_to_concept_id.get(edge.vocab2_id)
						if c1 is not None and c2 is not None:
							edges_list.append((c1, c2, float(edge.weight)))
				else:
					# Read from concept_connections table
					db_conns = session.exec(
						select(ConceptConnectionsModel).where(ConceptConnectionsModel.level == current_level)
					).all()
					for conn in db_conns:
						edges_list.append((conn.node1_id, conn.node2_id, float(conn.weight)))

				if not edges_list:
					print(f"No connections found at level {current_level}. Cannot collapse further.")
					break

				# Build igraph Graph for Leiden clustering
				sorted_ids = sorted(cast(list[int], concept_ids))
				concept_to_local_idx = {cid: idx for idx, cid in enumerate(sorted_ids)}
				
				igraph_edges = [(concept_to_local_idx[n1], concept_to_local_idx[n2]) for n1, n2, _ in edges_list]
				igraph_weights = [wt for _, _, wt in edges_list]

				g = ig.Graph(len(sorted_ids), igraph_edges, directed=False)
				cast(Any, g).es["weight"] = igraph_weights

				print(f"Graph constructed: {len(sorted_ids)} vertices, {len(igraph_edges)} edges")

				# Run Leiden clustering
				try:
					partition = cast(Any, la).find_partition(
						g,
						la.ModularityVertexPartition,
						weights="weight",
						seed=42
					)
				except Exception as exc:
					print(f"Leiden algorithm failed at level {current_level}: {exc}")
					break

				# Group local indexes into communities
				raw_communities: dict[int, list[int]] = defaultdict(list)
				for vertex_idx, community_idx in enumerate(partition.membership):
					raw_communities[community_idx].append(sorted_ids[vertex_idx])

				print(f"Detected {len(raw_communities)} communities at Level {current_level}")

				# Check if any clustering occurred (if communities count matches concept count, we cannot collapse further)
				if len(raw_communities) == len(sorted_ids):
					print("No communities collapsed. Stopping hierarchy construction.")
					break

				# Process each community to form collapsed level + 1 concepts
				new_concepts: list[ConceptsModel] = []
				parent_assignments: dict[int, int] = {} # child_concept_id -> parent_concept_id

				for comm_idx, member_ids in raw_communities.items():
					if len(member_ids) <= 1:
						# Do not collapse single-node communities further.
						# They remain as roots at the current level.
						continue

					# Filter edges belonging to this community
					member_set = set(member_ids)
					comm_edges = [
						(n1, n2, wt) for n1, n2, wt in edges_list if n1 in member_set and n2 in member_set
					]

					# Find leader using PageRank centrality
					leader_id, local_scores = _find_leader_and_scores(member_ids, comm_edges)
					leader_concept = concept_map[leader_id]

					# Create Level L+1 concept inheriting leader's vocab and label
					new_c = ConceptsModel(
						id=concept_id_sequence,
						level=current_level + 1,
						parent_id=None,
						vocab_id=leader_concept.vocab_id,
						label=leader_concept.label,
						pagerank_score=local_scores[leader_id],
						is_leader=True
					)
					new_concepts.append(new_c)

					# Assign parent ID, is_leader, and pagerank_score for child concepts
					for child_id in member_ids:
						parent_assignments[child_id] = concept_id_sequence
						c_record = concept_map[child_id]
						c_record.is_leader = (child_id == leader_id)
						c_record.pagerank_score = local_scores[child_id]
					
					concept_id_sequence += 1

				# Write Level L+1 concepts to DB
				session.add_all(new_concepts)
				session.flush()

				# Update Level L concepts with parent IDs and scores
				for child_id, parent_id in parent_assignments.items():
					c_record = concept_map[child_id]
					c_record.parent_id = parent_id
					session.add(c_record)
				
				session.flush()

				# Calculate Level L+1 concept connections by summing Level L connections
				next_level_connections: dict[tuple[int, int], float] = defaultdict(float)

				for n1, n2, wt in edges_list:
					p1 = parent_assignments.get(n1)
					p2 = parent_assignments.get(n2)
					if p1 is not None and p2 is not None and p1 != p2:
						node_pair = (min(cast(int, p1), cast(int, p2)), max(cast(int, p1), cast(int, p2)))
						next_level_connections[node_pair] += wt

				# Insert Level L+1 connections into DB
				print(f"Creating {len(next_level_connections)} connections at Level {current_level + 1}")
				new_conns_records: list[ConceptConnectionsModel] = []
				for (u, v), wt in next_level_connections.items():
					new_conns_records.append(
						ConceptConnectionsModel(
							id=concept_conn_id_sequence,
							level=current_level + 1,
							node1_id=u,
							node2_id=v,
							weight=wt
						)
					)
					concept_conn_id_sequence += 1

				session.add_all(new_conns_records)
				session.commit()

				print(f"Finished Level {current_level} -> {current_level + 1} processing.")
				
				# Termination check: if only 1 concept left at level L+1, we stop
				if len(new_concepts) <= 1:
					print("Collapsed into a single root concept. Hierarchy complete.")
					break

				current_level += 1

			print("\nHierarchical build complete!")

	finally:
		engine.dispose()


if __name__ == "__main__":
	# Default max hierarchy levels from config
	build_taxonomy_hierarchy()
