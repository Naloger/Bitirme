# -*- coding: utf-8 -*-
"""
FastMCP Server for Apache AGE operations.
Allows an LLM agent to interact with the Apache AGE 'memory_db' quadstore graph
(creating nodes, edges, deleting, updating, and executing raw Cypher).
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP

# Add backend directory to Python path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from Libs.Config.config import AGE_MEMORY_DB, AGE_RDF_GRAPH
from Scripts.infra.age.age_helpers import get_age_connection, parse_agtype, execute_cypher_param

# Initialize FastMCP Server
mcp = FastMCP("Apache_AGE_Operator")

def _run_param_query(cypher_query: str, params: dict, col_defs: str = "as (v agtype)") -> List[Any]:
    """Helper to run a parameterized Cypher query and return parsed agtype results."""
    conn = get_age_connection(AGE_MEMORY_DB)
    results = []
    try:
        with conn.cursor() as cur:
            # age_helpers.execute_cypher_param handles the prepared statement and $1 parameter mapping
            raw_tuples = execute_cypher_param(cur, AGE_RDF_GRAPH, cypher_query, params, col_defs)
            for row in raw_tuples:
                results.append(parse_agtype(row[0]))
    finally:
        conn.close()
    return results

@mcp.tool()
def execute_cypher(query: str, params: Optional[Dict[str, Any]] = None) -> str:
    """
    Execute a raw parameterized Cypher query on the memory database Apache AGE graph.
    Use standard Cypher placeholders (e.g., $my_param) and pass them in the params dict.
    DO NOT wrap the query in 'SELECT * FROM cypher(...)', provide only the raw Cypher.
    
    Example: 
        query: "MATCH (n:Person) WHERE n.name = $name RETURN n LIMIT 10"
        params: {"name": "Alice"}
    """
    try:
        p = params or {}
        data = _run_param_query(query, p)
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
        p = properties or {}
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
        if not properties:
            return json.dumps({"status": "warning", "message": "No properties provided to update."})
            
        set_clauses = ", ".join([f"n.{k} = ${k}" for k in properties.keys()])
        query = f"MATCH (n) WHERE id(n) = {node_id} SET {set_clauses} RETURN n"
        data = _run_param_query(query, properties)
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
        query = f"MATCH (n) WHERE id(n) = {node_id} DETACH DELETE n"
        _run_param_query(query, {})
        return json.dumps({"status": "success", "message": f"Node {node_id} and its edges were deleted."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def create_edge(start_node_id: int, edge_label: str, end_node_id: int, properties: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a directed edge with a given label from the start node to the end node.
    """
    try:
        p = properties or {}
        if not p:
            query = (
                f"MATCH (a), (b) "
                f"WHERE id(a) = {start_node_id} AND id(b) = {end_node_id} "
                f"CREATE (a)-[r:{edge_label}]->(b) "
                f"RETURN r"
            )
            data = _run_param_query(query, {})
        else:
            set_clauses = ", ".join([f"r.{k} = ${k}" for k in p.keys()])
            query = (
                f"MATCH (a), (b) "
                f"WHERE id(a) = {start_node_id} AND id(b) = {end_node_id} "
                f"CREATE (a)-[r:{edge_label}]->(b) "
                f"SET {set_clauses} "
                f"RETURN r"
            )
            data = _run_param_query(query, p)
            
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
        query = f"MATCH ()-[r]->() WHERE id(r) = {edge_id} DELETE r"
        _run_param_query(query, {})
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
        labels_query = "MATCH (n) RETURN DISTINCT label(n)"
        edge_types_query = "MATCH ()-[r]->() RETURN DISTINCT type(r)"
        
        labels_data = _run_param_query(labels_query, {})
        edge_types_data = _run_param_query(edge_types_query, {})
        
        schema = {
            "node_labels": labels_data,
            "edge_types": edge_types_data
        }
        return json.dumps({"status": "success", "schema": schema}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

if __name__ == "__main__":
    # Start the FastMCP server, exposing via standard input/output (stdio)
    mcp.run(transport='stdio')
