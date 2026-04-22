"""Test suite for Expression Tree (children_tree) CTT structure."""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Lib.CTT import CttTask, CttOperatorNode, CttTreeState, validate_ctt_tree


def test_simple_expression_tree():
    """Test simple binary expression tree: Task1 >> Task2."""
    tree: CttTreeState = {
        "root_tasks": [
            {
                "task_id": "root",
                "title": "Simple Sequence",
                "task_description": "Task1 >> Task2",
                "children_tree": [
                    {
                        "operator": "sequence",
                        "left": {
                            "task_id": "task1",
                            "title": "First Task",
                            "task_description": "Execute first"
                        },
                        "right": {
                            "task_id": "task2",
                            "title": "Second Task",
                            "task_description": "Execute second"
                        }
                    }
                ]
            }
        ]
    }

    errors = validate_ctt_tree(tree["root_tasks"])
    assert len(errors) == 0, f"Validation errors: {errors}"
    print("[PASS] Simple expression tree passed")


def test_complex_nested_expression_tree():
    """Test complex nested tree: Get_Details >> (Process_Card [] Process_PayPal)."""
    tree: CttTreeState = {
        "root_tasks": [
            {
                "task_id": "checkout",
                "title": "E-Commerce Checkout",
                "task_description": "Complete purchase workflow",
                "children_tree": [
                    {
                        "operator": "sequence",
                        "left": {
                            "task_id": "get_details",
                            "title": "Get Customer Details",
                            "task_description": "Collect customer information"
                        },
                        "right": {
                            "operator": "choice",
                            "left": {
                                "task_id": "cc_pay",
                                "title": "Process Credit Card",
                                "task_description": "Charge credit card"
                            },
                            "right": {
                                "task_id": "paypal_pay",
                                "title": "Process PayPal",
                                "task_description": "Use PayPal payment"
                            }
                        }
                    }
                ]
            }
        ]
    }

    errors = validate_ctt_tree(tree["root_tasks"])
    assert len(errors) == 0, f"Validation errors: {errors}"
    print("[PASS] Complex nested expression tree passed")
    print("       Visualized: Get_Details >> (Process_Card [] Process_PayPal)")


def test_deeply_nested_expression_tree():
    """Test deeply nested tree with multiple levels and operators."""
    tree: CttTreeState = {
        "root_tasks": [
            {
                "task_id": "workflow",
                "title": "Complex Workflow",
                "task_description": "Multi-step workflow with nested operators",
                "children_tree": [
                    {
                        "operator": "sequence",
                        "left": {
                            "task_id": "step1",
                            "title": "Step 1",
                            "task_description": "First sequential step"
                        },
                        "right": {
                            "operator": "sequence",
                            "left": {
                                "task_id": "step2",
                                "title": "Step 2",
                                "task_description": "Second sequential step"
                            },
                            "right": {
                                "operator": "interleaving",
                                "left": {
                                    "task_id": "parallel1",
                                    "title": "Parallel Task 1",
                                    "task_description": "Run in parallel"
                                },
                                "right": {
                                    "task_id": "parallel2",
                                    "title": "Parallel Task 2",
                                    "task_description": "Run in parallel"
                                }
                            }
                        }
                    }
                ]
            }
        ]
    }

    errors = validate_ctt_tree(tree["root_tasks"])
    assert len(errors) == 0, f"Validation errors: {errors}"
    print("[PASS] Deeply nested expression tree passed")
    print("       Visualized: Step1 >> (Step2 >> (Parallel1 ||| Parallel2))")


def test_json_serialization_expression_tree():
    """Test that expression trees serialize properly to JSON."""
    tree: CttTreeState = {
        "root_tasks": [
            {
                "task_id": "root",
                "title": "JSON Test",
                "task_description": "Test JSON serialization",
                "children_tree": [
                    {
                        "operator": "choice",
                        "left": {
                            "task_id": "option_a",
                            "title": "Option A",
                            "task_description": "First choice"
                        },
                        "right": {
                            "task_id": "option_b",
                            "title": "Option B",
                            "task_description": "Second choice"
                        }
                    }
                ]
            }
        ]
    }

    # Serialize to JSON
    json_str = json.dumps(tree, indent=2)

    # Deserialize back
    reloaded = json.loads(json_str)

    # Validate reloaded tree
    errors = validate_ctt_tree(reloaded["root_tasks"])
    assert len(errors) == 0, f"Validation errors after JSON round-trip: {errors}"
    print("[PASS] JSON serialization round-trip passed")


def test_mixed_flat_and_expression_tree():
    """Test using both old-style flat children and new-style expression tree in same workflow."""
    tree: CttTreeState = {
        "root_tasks": [
            {
                "task_id": "mixed",
                "title": "Mixed Structure Root",
                "task_description": "Root with both child styles",
                # Old-style flat children
                "children": [
                    {
                        "task_id": "old_style_child",
                        "title": "Old Style Child",
                        "task_description": "Using flat children array"
                    }
                ]
            },
            {
                "task_id": "tree_style",
                "title": "Expression Tree Root",
                "task_description": "Root with expression tree children",
                # New-style expression tree
                "children_tree": [
                    {
                        "operator": "sequence",
                        "left": {
                            "task_id": "left_task",
                            "title": "Left Task",
                            "task_description": "Left side of operator"
                        },
                        "right": {
                            "task_id": "right_task",
                            "title": "Right Task",
                            "task_description": "Right side of operator"
                        }
                    }
                ]
            }
        ]
    }

    errors = validate_ctt_tree(tree["root_tasks"])
    # Should be valid - both styles can coexist in same workflow
    assert len(errors) == 0, f"Validation errors: {errors}"
    print("[PASS] Mixed flat and expression tree styles passed")


def test_operator_aliases_in_expression_tree():
    """Test that operator aliases work in expression trees."""
    from Agents.Nodes.node_task_master.node_TaskMaster import _coerce_node

    # Test with operator alias ">>"
    node_dict = {
        "operator": ">>",  # Using alias instead of "sequence"
        "left": {
            "task_id": "a",
            "title": "A",
            "task_description": "Task A"
        },
        "right": {
            "task_id": "b",
            "title": "B",
            "task_description": "Task B"
        }
    }

    coerced = _coerce_node(node_dict)
    assert coerced is not None, "Failed to coerce node with >> alias"
    assert isinstance(coerced, dict), "Coerced node should be dict"
    assert coerced.get("operator") == "sequence", ">> should normalize to sequence"
    print("[PASS] Operator alias '>>' works in expression tree")


if __name__ == "__main__":
    print("Running Expression Tree CTT Tests...\n")

    test_simple_expression_tree()
    test_complex_nested_expression_tree()
    test_deeply_nested_expression_tree()
    test_json_serialization_expression_tree()
    test_mixed_flat_and_expression_tree()
    test_operator_aliases_in_expression_tree()

    print("\n[OK] All expression tree tests passed!")

