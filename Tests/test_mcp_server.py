# -*- coding: utf-8 -*-
"""
Integration tests for the Apache AGE MCP Server.
Tests that the MCP tools correctly interact with the memory_db via psycopg2.
"""

import sys
import json
import pytest
from pathlib import Path

# Ensure project root is in the path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Import the tool functions from the MCP server
from Scripts.mcp.age_mcp_server import (
    get_graph_schema,
    create_node,
    update_node,
    delete_node,
    create_edge,
    delete_edge,
    execute_cypher
)

@pytest.fixture(scope="module")
def cleanup_test_nodes():
    """Ensure any left-over test nodes are cleaned up before and after tests."""
    def clean():
        execute_cypher("MATCH (n:TestMCPNode) DETACH DELETE n", {})
    clean()
    yield
    clean()

def test_mcp_schema():
    """Test retrieving the graph schema."""
    result_str = get_graph_schema()
    result = json.loads(result_str)
    
    assert result["status"] == "success"
    assert "schema" in result
    assert "node_labels" in result["schema"]
    assert "edge_types" in result["schema"]

def test_mcp_crud_lifecycle(cleanup_test_nodes):
    """Test creating nodes, updating, creating edges, querying, and deleting them via MCP tools."""
    
    # 1. Create Node A
    node_a_res = json.loads(create_node("TestMCPNode", {"name": "Node A", "value": 10}))
    if node_a_res["status"] != "success":
        print(f"CREATE NODE ERROR: {node_a_res}")
    assert node_a_res["status"] == "success"
    assert len(node_a_res["data"]) == 1
    node_a_id = node_a_res["data"][0]["id"]
    
    # 2. Create Node B
    node_b_res = json.loads(create_node("TestMCPNode", {"name": "Node B", "value": 20}))
    assert node_b_res["status"] == "success"
    node_b_id = node_b_res["data"][0]["id"]
    
    # 3. Update Node A
    update_res = json.loads(update_node(node_a_id, {"status": "updated", "value": 15}))
    assert update_res["status"] == "success"
    updated_props = update_res["data"][0]["properties"]
    assert updated_props["name"] == "Node A"  # existing property preserved
    assert updated_props["status"] == "updated"  # new property added
    assert updated_props["value"] == 15  # existing property modified

    # 4. Create Edge between Node A and Node B
    edge_res = json.loads(create_edge(node_a_id, "TEST_LINKS_TO", node_b_id, {"weight": 0.9}))
    assert edge_res["status"] == "success"
    assert len(edge_res["data"]) == 1
    edge_id = edge_res["data"][0]["id"]
    edge_props = edge_res["data"][0]["properties"]
    assert edge_props["weight"] == 0.9

    # 5. Execute Cypher to verify relationship
    # Return just the start node to avoid parse_agtype splitting on internal ::edge/::vertex tokens inside lists
    query_list = "MATCH (a:TestMCPNode)-[r:TEST_LINKS_TO]->(b:TestMCPNode) WHERE a.name = $start_name RETURN a"
    cypher_res_list = json.loads(execute_cypher(query_list, {"start_name": "Node A"}))
    assert cypher_res_list["status"] == "success"
    assert len(cypher_res_list["results"]) == 1
    row_data = cypher_res_list["results"][0]
    if isinstance(row_data, str):
        row_data = json.loads(row_data)
    assert row_data["label"] == "TestMCPNode"

    # 6. Delete Edge
    del_edge_res = json.loads(delete_edge(edge_id))
    assert del_edge_res["status"] == "success"

    # 7. Delete Nodes
    del_node_a_res = json.loads(delete_node(node_a_id))
    assert del_node_a_res["status"] == "success"
    del_node_b_res = json.loads(delete_node(node_b_id))
    assert del_node_b_res["status"] == "success"

    # 8. Verify Deletion
    verify_res = json.loads(execute_cypher("MATCH (n:TestMCPNode) RETURN n", {}))
    assert verify_res["status"] == "success"
    assert len(verify_res["results"]) == 0
