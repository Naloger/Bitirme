"""Build hierarchical communities recursively using Leiden and PageRank.

Level 0 is initialized from vocabulary entries present in the PPMI lemma matrix.
Subsequent levels are collapsed using the concept_connections of the previous level.
"""

from __future__ import annotations
from collections import defaultdict
from typing import Any, cast

# Add backend directory to Python path if running script directly
# sys.path.append(str(Path(__file__).resolve().parent.parent))

import igraph as ig
import leidenalg as la
from sqlmodel import select, delete
from sqlalchemy import func

from Config.config import LEMMA_MATRIX_DATABASE_PATH, BUILD_HIERARCHY_MAX_LEVELS
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
	g_any: Any = g
	g_any.es["weight"] = igraph_weights

	# Calculate PageRank
	try:
		scores = g_any.pagerank(weights="weight")
	except Exception:  # noqa: PyBroadException
		# Fallback to unweighted PageRank if weighted fails
		try:
			scores = g_any.pagerank()
		except Exception:  # noqa: PyBroadException
			# Fallback to degree centrality if PageRank fails
			degrees = g_any.degree()
			total_deg = float(sum(degrees) or 1.0)
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
			# Wrap all mutations in a single transaction block to prevent database corruption on partial failure (Bug 11)
			with session.begin():
				# Clear existing hierarchy tables
				print("Clearing concepts and concept_connections tables...")
				session.exec(delete(ConceptConnectionsModel))
				session.exec(delete(ConceptsModel))

				# 1. Initialize Level 0 (Base vocabulary words present in PPMI matrix)
				print("Initializing Level 0 base concepts from vocabulary in PPMI matrix...")
				
				# Get unique vocabulary IDs in PPMI table (Bug 6: load and isolate immediately)
				raw_edges = session.exec(select(PPMILemmaMatrixModel)).all()
				raw_vocab_ids = set()
				for edge in raw_edges:
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

				# Filter ppmi_edges to only include valid pairs
				valid_edges = [
					edge for edge in raw_edges
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
				session.flush() # Flush to generate IDs inside the database transaction
				
				# Re-query Level 0 concepts to ensure IDs are correctly populated in memory (Bug 1)
				level_0_concepts = session.exec(
					select(ConceptsModel).where(ConceptsModel.level == 0)
				).all()
				
				# Create map of vocab_id -> concept_id for Level 0
				vocab_id_to_concept_id = {
					c.vocab_id: c.id for c in level_0_concepts if c.vocab_id is not None and c.id is not None
				}

				current_level = 0
				
				# Query the database to resolve current MAX(id) to avoid sequence key collisions (Bug 2)
				max_c_id = session.exec(select(func.max(ConceptsModel.id))).first() or 0
				concept_id_sequence = max_c_id + 1

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
					raw_edges_list: list[tuple[int, int, float]] = []

					if current_level == 0:
						# Read from valid_edges
						for edge in valid_edges:
							c1 = vocab_id_to_concept_id.get(edge.vocab1_id)
							c2 = vocab_id_to_concept_id.get(edge.vocab2_id)
							if c1 is not None and c2 is not None:
								raw_edges_list.append((c1, c2, float(edge.weight)))
					else:
						# Read from concept_connections table
						db_conns = session.exec(
							select(ConceptConnectionsModel).where(ConceptConnectionsModel.level == current_level)
						).all()
						for conn in db_conns:
							raw_edges_list.append((conn.node1_id, conn.node2_id, float(conn.weight)))

					if not raw_edges_list and current_level > 0:
						print(f"No connections found at level {current_level}. Cannot collapse further.")
						break

					# Deduplicate symmetric edges and remove self-loops before clustering (Bug 7)
					deduped_edges: dict[tuple[int, int], float] = defaultdict(float)
					for n1, n2, wt in raw_edges_list:
						u, v = min(n1, n2), max(n1, n2)
						if u != v:
							deduped_edges[(u, v)] += wt
					edges_list = [(u, v, wt) for (u, v), wt in deduped_edges.items()]

					# Build igraph Graph for Leiden clustering
					sorted_ids = sorted(cast(list[int], concept_ids))
					concept_to_local_idx = {cid: idx for idx, cid in enumerate(sorted_ids)}
					
					igraph_edges = [(concept_to_local_idx[n1], concept_to_local_idx[n2]) for n1, n2, _ in edges_list]
					igraph_weights = [wt for _, _, wt in edges_list]

					# Run Leiden clustering if edges exist
					partition_membership = []
					if igraph_edges:
						g = ig.Graph(len(sorted_ids), igraph_edges, directed=False)
						g_any: Any = g
						g_any.es["weight"] = igraph_weights # Clean typing casting (Bug 10)
						print(f"Graph constructed: {len(sorted_ids)} vertices, {len(igraph_edges)} edges")

						try:
							partition = cast(Any, la).find_partition(
								g,
								la.ModularityVertexPartition,
								weights="weight",
								seed=42
							)
							partition_membership = partition.membership
						except Exception as exc:
							print(f"Leiden algorithm failed at level {current_level}: {exc}")
							break
					else:
						# If there are no connections, every node gets its own community
						print(f"No connections at level {current_level}. Treating all concepts as singletons.")
						partition_membership = list(range(len(sorted_ids)))

					# Group local indexes into communities
					raw_communities: dict[int, list[int]] = defaultdict(list)
					for vertex_idx, community_idx in enumerate(partition_membership):
						raw_communities[community_idx].append(sorted_ids[vertex_idx])

					print(f"Detected {len(raw_communities)} communities at Level {current_level}")

					# Check if any clustering occurred
					# (If communities count equals node count, no collapsing can happen)
					if len(raw_communities) == len(sorted_ids):
						print("No communities collapsed. Stopping hierarchy construction.")
						break

					# Process each community to form collapsed level + 1 concepts
					new_concepts: list[ConceptsModel] = []
					parent_assignments: dict[int, int] = {} # child_concept_id -> parent_concept_id

					for comm_idx, member_ids in raw_communities.items():
						if len(member_ids) <= 1:
							# Promote single-node communities to next level to prevent orphaning (Bug 3)
							child_id = member_ids[0]
							child_concept = concept_map[child_id]
							new_c = ConceptsModel(
								id=concept_id_sequence,
								level=current_level + 1,
								parent_id=None,
								vocab_id=child_concept.vocab_id,
								label=child_concept.label,
								pagerank_score=child_concept.pagerank_score or 1.0,
								is_leader=True
							)
							new_concepts.append(new_c)
							parent_assignments[child_id] = concept_id_sequence
							
							child_concept.is_leader = True
							child_concept.pagerank_score = child_concept.pagerank_score or 1.0
							
							concept_id_sequence += 1
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

					# Update Level L concepts with parent IDs (Bug 9: direct mutation, no loop add())
					for child_id, parent_id in parent_assignments.items():
						concept_map[child_id].parent_id = parent_id
					
					session.flush()

					# Calculate Level L+1 concept connections by summing Level L connections (Bug 5 resolved)
					next_level_connections: dict[tuple[int, int], float] = defaultdict(float)

					for n1, n2, wt in edges_list:
						p1 = parent_assignments.get(n1)
						p2 = parent_assignments.get(n2)
						if p1 is not None and p2 is not None and p1 != p2:
							node_pair = (min(p1, p2), max(p1, p2))
							next_level_connections[node_pair] += wt

					# Insert Level L+1 connections into DB (Bug 2: omit 'id' to let DB auto-increment)
					print(f"Creating {len(next_level_connections)} connections at Level {current_level + 1}")
					new_conns_records: list[ConceptConnectionsModel] = []
					for (u, v), wt in next_level_connections.items():
						new_conns_records.append(
							ConceptConnectionsModel(
								level=current_level + 1,
								node1_id=u,
								node2_id=v,
								weight=wt
							)
						)

					session.add_all(new_conns_records)
					session.flush()

					print(f"Finished Level {current_level} -> {current_level + 1} processing.")
					
					# Termination check: check total count at next level, including singletons (Bug 4 resolved)
					if len(new_concepts) <= 1:
						print("Collapsed into a single root concept. Hierarchy complete.")
						break

					current_level += 1

			# Commit transaction atomically
			print("\nHierarchical build complete and committed successfully!")

	finally:
		engine.dispose()


if __name__ == "__main__":
	# Default max hierarchy levels from config
	build_taxonomy_hierarchy()
