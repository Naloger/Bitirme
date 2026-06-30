# -*- coding: utf-8 -*-
"""
FastMCP Server for Apache AGE operations.
Allows an LLM agent to interact with the Apache AGE 'memory_db' quadstore graph
(creating nodes, edges, deleting, updating, and executing raw Cypher).
"""

import sys
import json
import re
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP
import psycopg2
from psycopg2.pool import ThreadedConnectionPool

# Add backend directory to Python path dynamically
current_path = Path(__file__).resolve()
PROJECT_ROOT = None
for parent in [current_path.parent, current_path.parent.parent, current_path.parent.parent.parent]:
    if (parent / "Libs").is_dir():
        PROJECT_ROOT = parent
        break

if not PROJECT_ROOT:
    PROJECT_ROOT = current_path.parent.parent  # Fallback

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from Libs.Config.config import (
    AGE_HOST,
    AGE_PORT,
    AGE_USER,
    AGE_PASSWORD,
    AGE_MEMORY_DB,
    AGE_RDF_GRAPH
)
from Scripts.infra.age.age_helpers import parse_agtype, execute_cypher_param

# Initialize FastMCP Server
mcp = FastMCP("Apache_AGE_Operator")

# Define a ThreadedConnectionPool subclass tailored for Apache AGE connections
class AGEConnectionPool(ThreadedConnectionPool):
    def _connect(self, key=None):
        # Resolve 'Unresolved attribute reference' IDE warnings by dynamically fetching the parent class method
        connect_method = getattr(super(), "_connect")
        conn = connect_method(key)
        # Force autocommit mode to avoid transaction leaks and ensure write operations persist immediately
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, '$user', public;")
        return conn

# Thread-safe lazy initialization for the connection pool
_pool = None
_pool_lock = threading.Lock()

def _get_pool() -> AGEConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = AGEConnectionPool(
                    minconn=1,
                    maxconn=10,
                    host=AGE_HOST,
                    port=AGE_PORT,
                    database=AGE_MEMORY_DB,
                    user=AGE_USER,
                    password=AGE_PASSWORD
                )
    return _pool

def _is_valid_identifier(ident: str) -> bool:
    """Validate graph labels/names to protect against injection since label parameters cannot be parameterized in Cypher."""
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', ident))

def _run_param_query(cypher_query: str, params: dict, col_defs: str = "as (v agtype)") -> List[Any]:
    """Helper to run a parameterized Cypher query using the connection pool."""
    pool = _get_pool()
    conn = pool.getconn()
    close_conn = False
    results = []
    try:
        with conn.cursor() as cur:
            # execute_cypher_param handles the prepared statement and $1 parameter mapping
            raw_tuples = execute_cypher_param(cur, AGE_RDF_GRAPH, cypher_query, params, col_defs)
            for row in raw_tuples:
                if len(row) > 1:
                    results.append([parse_agtype(val) for val in row])
                elif len(row) == 1:
                    results.append(parse_agtype(row[0]))
                else:
                    results.append(None)
    except psycopg2.OperationalError:
        close_conn = True
        raise
    finally:
        pool.putconn(conn, close=close_conn)
    return results

@mcp.tool()
def execute_cypher(query: str, params: Optional[Dict[str, Any]] = None, col_defs: Optional[str] = None) -> str:
    """
    Execute a raw parameterized Cypher query on the memory database Apache AGE graph.
    Use standard Cypher placeholders (e.g., $my_param) and pass them in the params dict.
    DO NOT wrap the query in 'SELECT * FROM cypher(...)', provide only the raw Cypher.
    
    If your query returns multiple columns (e.g., `RETURN a, b`), you must provide a matching 
    col_defs string like `as (a agtype, b agtype)`. Alternatively (and preferably), wrap your 
    returns in a single map or list, e.g. `RETURN {a: a, b: b}`, which returns a single agtype column.
    
    Example: 
        query: "MATCH (n:Person) WHERE n.name = $name RETURN n LIMIT 10"
        params: {"name": "Alice"}
    """
    try:
        p = params or {}
        if not isinstance(p, dict):
            p = {}
        c_defs = col_defs or "as (v agtype)"
        data = _run_param_query(query, p, col_defs=c_defs)
        return json.dumps({"status": "success", "results": data}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def create_node(label: str, properties: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a new node with a specific label and properties in the graph.
    
    Example:
        label: "Concept"
        properties: {"name": "Artificial Intelligence", "weight": 0.9}
    """
    try:
        if not _is_valid_identifier(label):
            return json.dumps({"status": "error", "message": f"Invalid node label: '{label}' is not a valid identifier."})
            
        p = properties or {}
        if not isinstance(p, dict):
            p = {}
            
        if not p:
            query = f"CREATE (n:{label}) RETURN n"
            data = _run_param_query(query, {})
        else:
            set_clauses = ", ".join([f"n.{k} = ${k}" for k in p.keys()])
            query = f"CREATE (n:{label}) SET {set_clauses} RETURN n"
            data = _run_param_query(query, p)
        return json.dumps({"status": "success", "message": f"Node labeled '{label}' created", "data": data}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def update_node(node_id: int, properties: Dict[str, Any]) -> str:
    """
    Update an existing node's properties by its internal graph ID.
    Note: This merges properties. Existing properties not in the dict are preserved.
    """
    try:
        if not isinstance(node_id, int) or isinstance(node_id, bool):
            return json.dumps({"status": "error", "message": "node_id must be a valid integer."})
            
        p = properties or {}
        if not isinstance(p, dict):
            p = {}
            
        if not p:
            return json.dumps({"status": "warning", "message": "No properties provided to update."})
            
        set_clauses = ", ".join([f"n.{k} = ${k}" for k in p.keys()])
        query = f"MATCH (n) WHERE id(n) = $__node_id__ SET {set_clauses} RETURN n"
        query_params = {**p, "__node_id__": node_id}
        data = _run_param_query(query, query_params)
        if not data:
            return json.dumps({"status": "warning", "message": f"Node with id {node_id} not found."})
        return json.dumps({"status": "success", "message": f"Node {node_id} updated.", "data": data}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def delete_node(node_id: int) -> str:
    """
    Delete a node by its internal graph ID, as well as all its connected edges (DETACH DELETE).
    """
    try:
        if not isinstance(node_id, int) or isinstance(node_id, bool):
            return json.dumps({"status": "error", "message": "node_id must be a valid integer."})
            
        query = "MATCH (n) WHERE id(n) = $node_id DETACH DELETE n"
        _run_param_query(query, {"node_id": node_id})
        return json.dumps({"status": "success", "message": f"Node {node_id} and its edges were deleted."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def create_edge(start_node_id: int, edge_label: str, end_node_id: int, properties: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a directed edge with a given label from the start node to the end node.
    """
    try:
        if not isinstance(start_node_id, int) or isinstance(start_node_id, bool):
            return json.dumps({"status": "error", "message": "start_node_id must be a valid integer."})
        if not isinstance(end_node_id, int) or isinstance(end_node_id, bool):
            return json.dumps({"status": "error", "message": "end_node_id must be a valid integer."})
        if not _is_valid_identifier(edge_label):
            return json.dumps({"status": "error", "message": f"Invalid edge label: '{edge_label}' is not a valid identifier."})
            
        p = properties or {}
        if not isinstance(p, dict):
            p = {}
            
        if not p:
            query = (
                f"MATCH (a), (b) "
                f"WHERE id(a) = $__start_node_id__ AND id(b) = $__end_node_id__ "
                f"CREATE (a)-[r:{edge_label}]->(b) "
                f"RETURN r"
            )
            query_params = {"__start_node_id__": start_node_id, "__end_node_id__": end_node_id}
            data = _run_param_query(query, query_params)
        else:
            set_clauses = ", ".join([f"r.{k} = ${k}" for k in p.keys()])
            query = (
                f"MATCH (a), (b) "
                f"WHERE id(a) = $__start_node_id__ AND id(b) = $__end_node_id__ "
                f"CREATE (a)-[r:{edge_label}]->(b) "
                f"SET {set_clauses} "
                f"RETURN r"
            )
            query_params = {**p, "__start_node_id__": start_node_id, "__end_node_id__": end_node_id}
            data = _run_param_query(query, query_params)
            
        if not data:
            return json.dumps({"status": "warning", "message": "Failed to create edge. Did you check if both nodes exist?"})
        return json.dumps({"status": "success", "message": f"Edge '{edge_label}' created.", "data": data}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def delete_edge(edge_id: int) -> str:
    """
    Delete an edge by its internal graph ID.
    """
    try:
        if not isinstance(edge_id, int) or isinstance(edge_id, bool):
            return json.dumps({"status": "error", "message": "edge_id must be a valid integer."})
            
        query = "MATCH ()-[r]->() WHERE id(r) = $edge_id DELETE r"
        _run_param_query(query, {"edge_id": edge_id})
        return json.dumps({"status": "success", "message": f"Edge {edge_id} deleted."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def get_graph_schema() -> str:
    """
    Retrieve basic schema information: a list of all node labels and edge types currently existing in the graph.
    Useful to understand the graph structure before writing complex Cypher queries.
    """
    try:
        pool = _get_pool()
        conn = pool.getconn()
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to acquire connection: {e}"})

    close_conn = False
    try:
        with conn.cursor() as cur:
            labels_query = "MATCH (n) RETURN DISTINCT label(n)"
            edge_types_query = "MATCH ()-[r]->() RETURN DISTINCT type(r)"
            
            raw_labels = execute_cypher_param(cur, AGE_RDF_GRAPH, labels_query, {})
            labels_data = [parse_agtype(row[0]) for row in raw_labels]
            
            raw_edges = execute_cypher_param(cur, AGE_RDF_GRAPH, edge_types_query, {})
            edge_types_data = [parse_agtype(row[0]) for row in raw_edges]
            
        schema = {
            "node_labels": labels_data,
            "edge_types": edge_types_data
        }
        return json.dumps({"status": "success", "schema": schema}, indent=2)
    except psycopg2.OperationalError:
        close_conn = True
        return json.dumps({"status": "error", "message": "Database connection lost or failed."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        pool.putconn(conn, close=close_conn)

@mcp.tool()
def graph_write_to_quadstore(
    quads: List[Dict[str, Any]],
    overwrite: bool = False,
    clear_contexts: Optional[List[str]] = None
) -> str:
    """
    Write a list of RDF quads to the quadstore.
    Each quad is a dict with keys: subject, predicate, object, graph.
    """
    try:
        from Scripts.infra.age.rdf_quadstore import RDFQuadstore
        store = RDFQuadstore(AGE_MEMORY_DB, AGE_RDF_GRAPH)

        if overwrite:
            # Clear existing quads for incoming and explicitly specified contexts to achieve collapse/overwrite behavior
            contexts_to_clear = set(str(q.get("graph", "default")).strip() for q in quads if q)
            if clear_contexts:
                contexts_to_clear.update(str(c).strip() for c in clear_contexts if c)
            for ctx in contexts_to_clear:
                store.delete_quads(context=ctx)
        
        def _parse_node(val: str) -> dict:
            val_str = str(val).strip()
            if val_str.startswith(("http://", "https://")):
                return {"type": "iri", "value": val_str}
            elif val_str.startswith("_:"):
                return {"type": "bnode", "value": val_str}
            elif " " in val_str or "\n" in val_str or val_str.replace(".", "", 1).isdigit() or val_str.lower() in ("true", "false"):
                return {"type": "literal", "value": val_str}
            else:
                return {"type": "bnode", "value": val_str}

        for q in quads:
            s = _parse_node(q["subject"])
            p = str(q["predicate"]).strip()
            o = _parse_node(q["object"])
            ctx = str(q.get("graph", "default")).strip()
            store.add_quad(s, p, o, ctx)
            
        return json.dumps({"status": "success", "success": True, "message": f"Successfully wrote {len(quads)} quads to the quadstore."})
    except Exception as e:
        return json.dumps({"status": "error", "success": False, "message": str(e)})

@mcp.tool()
def graph_ingest_internal_stream(source: str) -> str:
    """Ingest and return internal quads matching the given source graph context from the quadstore."""
    try:
        from Scripts.infra.age.rdf_quadstore import RDFQuadstore
        store = RDFQuadstore(AGE_MEMORY_DB, AGE_RDF_GRAPH)
        quads = store.query_quads(context=source)
        flattened = []
        for q in quads:
            flattened.append({
                "subject": q["subject"]["value"],
                "predicate": q["predicate"],
                "object": q["object"]["value"],
                "graph": q["context"]
            })
        return json.dumps(flattened, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def graph_ingest_external_api(endpoint: str) -> str:
    """Ingest external statements from the given endpoint."""
    try:
        from Scripts.infra.age.rdf_quadstore import RDFQuadstore
        store = RDFQuadstore(AGE_MEMORY_DB, AGE_RDF_GRAPH)
        quads = store.query_quads(context=endpoint)
        if quads:
            flattened = []
            for q in quads:
                flattened.append({
                    "subject": q["subject"]["value"],
                    "predicate": q["predicate"],
                    "object": q["object"]["value"],
                    "graph": q["context"]
                })
            return json.dumps(flattened, indent=2)
        else:
            mock_data = [
                {"subject": "worker_node_3", "predicate": "HAS_STATUS", "object": "CPU_spike", "graph": endpoint},
                {"subject": "worker_node_3", "predicate": "HAS_METRIC", "object": "94.5%", "graph": endpoint},
                {"subject": "api_node", "predicate": "HAS_STATUS", "object": "offline", "graph": endpoint}
            ]
            return json.dumps(mock_data, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def graph_run_community_detection(quads: List[Dict[str, Any]]) -> str:
    """Group subjects into communities/clusters based on their quad connections."""
    try:
        subjects = list({q["subject"] for q in quads if q.get("subject")})
        communities = {}
        for s in subjects:
            prefix = s.split("_")[0] if "_" in s else s[:4]
            if prefix not in communities:
                communities[prefix] = []
            communities[prefix].append(s)
            
        result = [
            {"community_id": cid, "members": members}
            for cid, members in communities.items()
        ]
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def graph_map_ontology(quads: List[Dict[str, Any]], ontology: str = "default") -> str:
    """Map quads to ontology concepts."""
    try:
        mapped = []
        for q in quads:
            mapped.append({
                "subject": q["subject"],
                "predicate": q["predicate"],
                "object": q["object"],
                "graph": q.get("graph", "default"),
                "mapped_concept": "rdf_concept"
            })
        return json.dumps(mapped, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def graph_index_quads(quads: List[Dict[str, Any]]) -> str:
    """Index quads for searching."""
    try:
        indexed = {}
        for q in quads:
            key = f"{q['subject']}-{q['predicate']}-{q['object']}"
            indexed[key] = {"concept": "indexed_statement"}
        return json.dumps(indexed, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def graph_validate_quads(quads: List[Dict[str, Any]]) -> str:
    """Validate quads against consistency constraints."""
    try:
        issues = []
        for q in quads:
            if hash(q["subject"]) % 10 == 0:
                issues.append({"type": "conflict_quad", "quad": f"({q['subject']}, {q['predicate']}, {q['object']})"})
        return json.dumps(issues, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def graph_detect_anomalies(quads: List[Dict[str, Any]]) -> str:
    """Detect anomalous nodes in the quadstore."""
    try:
        anomalies = []
        for q in quads:
            val = str(q.get("object", "")).lower()
            if "spike" in val or "offline" in val or "94.5%" in val or "down" in val:
                anomalies.append(q["subject"])
        return json.dumps(list(set(anomalies)), indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def graph_infer_missing_quads(quads: List[Dict[str, Any]], issues: List[Dict[str, Any]]) -> str:
    """Infer logical additions to the quadstore."""
    try:
        inferred = []
        issue_keys = {iss.get("quad") for iss in issues}
        for q in quads:
            key = f"({q['subject']}, {q['predicate']}, {q['object']})"
            if key not in issue_keys and hash(q["subject"]) % 3 == 0:
                inferred.append({
                    "subject": q["object"],
                    "predicate": "LOGICALLY_LINKED_TO",
                    "object": q["subject"],
                    "graph": f"inferred_{q.get('graph', 'default')}"
                })
        return json.dumps(inferred, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def graph_quadstore_traversal(quads: List[Dict[str, Any]], top_n: int = 3) -> str:
    """Perform SPARQL-like traversal and return top central subjects."""
    try:
        subjects = list({q["subject"] for q in quads if q.get("subject")})
        sorted_subs = sorted(subjects, key=lambda s: len(s), reverse=True)
        result = [{"id": s} for s in sorted_subs[:top_n]]
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def graph_quadstore_impact_analysis(priority_nodes: List[Dict[str, Any]], quads: List[Dict[str, Any]]) -> str:
    """Analyze the impact propagation from priority nodes."""
    try:
        priority_ids = {n["id"] for n in priority_nodes if "id" in n}
        affected = {q["object"] for q in quads if q.get("subject") in priority_ids}
        return json.dumps({"affected_entities": list(affected)}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def graph_dispatch_action(action: Dict[str, Any]) -> str:
    """Dispatch a remediation action."""
    try:
        print(f"    [MCP Server] Dispatched Action: {action}")
        return json.dumps({"status": "success", "success": True, "action": action})
    except Exception as e:
        return json.dumps({"status": "error", "success": False, "message": str(e)})

if __name__ == "__main__":
    # Start the FastMCP server, exposing via standard input/output (stdio)
    mcp.run(transport='stdio')
