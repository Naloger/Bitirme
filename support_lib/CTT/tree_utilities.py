"""Utility functions for visualizing and manipulating CTT Expression Trees."""

from __future__ import annotations

from typing import Any


def visualize_expression_tree(node: Any, depth: int = 0, is_right: bool = False) -> str:
    """Generate ASCII art visualization of expression tree.

    Args:
        node: CttTask or CttOperatorNode
        depth: Current recursion depth
        is_right: Whether this is a right child (affects indentation)

    Returns:
        ASCII art string representation

    Example:
        >>> tree = {"operator": "sequence", "left": {...}, "right": {...}}
        >>> print(visualize_expression_tree(tree))
        Sequence (>>)
        ├── Left Task
        └── Right Task
    """
    if not isinstance(node, dict):
        return ""

    lines = []
    indent = "  " * depth
    connector = "└── " if is_right else "├── "

    if "operator" in node:
        # It's an operator node
        operator = node.get("operator", "unknown")
        operator_symbols = {
            "sequence": ">>",
            "choice": "[]",
            "interleaving": "|||",
            "order_independence": "|=|",
            "suspend_resume": "|>",
            "disabling": "[>",
            "synchronization": "|[]|",
        }
        symbol = operator_symbols.get(operator, operator)

        lines.append(f"{indent}{connector}{operator.upper()} ({symbol})")

        # Visualize left and right children
        left = node.get("left")
        right = node.get("right")

        if left:
            left_lines = visualize_expression_tree(left, depth + 1, is_right=False).split("\n")
            lines.extend([l for l in left_lines if l])

        if right:
            right_lines = visualize_expression_tree(right, depth + 1, is_right=True).split("\n")
            lines.extend([l for l in right_lines if l])
    else:
        # It's a task node
        task_id = node.get("task_id", "unknown")
        title = node.get("title", "Untitled")
        lines.append(f"{indent}{connector}{title} ({task_id})")

    return "\n".join(lines)


def linearize_expression_tree(node: Any) -> str:
    """Convert expression tree to linear notation (left-to-right reading).

    Args:
        node: CttTask or CttOperatorNode

    Returns:
        String representation like "Task1 >> (Task2 [] Task3)"

    Example:
        >>> tree = {"operator": "sequence",
        ...         "left": {"task_id": "1", "title": "A"},
        ...         "right": {"task_id": "2", "title": "B"}}
        >>> linearize_expression_tree(tree)
        'A >> B'
    """
    if not isinstance(node, dict):
        return ""

    operator_symbols = {
        "sequence": ">>",
        "choice": "[]",
        "interleaving": "|||",
        "order_independence": "|=|",
        "suspend_resume": "|>",
        "disabling": "[>",
        "synchronization": "|[]|",
    }

    if "operator" in node:
        # Operator node
        operator = node.get("operator", "")
        symbol = operator_symbols.get(operator, operator)

        left_expr = linearize_expression_tree(node.get("left"))
        right_expr = linearize_expression_tree(node.get("right"))

        # Add parentheses if right side is complex
        if "operator" in (node.get("right") or {}):
            right_expr = f"({right_expr})"

        return f"{left_expr} {symbol} {right_expr}".strip()
    else:
        # Task node
        return node.get("title", node.get("task_id", "?"))


def flatten_expression_tree(node: Any, parent_operator: str = "sequence") -> dict[str, Any]:
    """Convert expression tree back to flat children structure (lossy).

    Note: This is lossy - we lose the binary operator placement information.
    The resulting flat structure uses a single operator for all children.

    Args:
        node: CttTask or CttOperatorNode
        parent_operator: Default operator to use for flattened structure

    Returns:
        Task dict with flat children list and single operator
    """
    if not isinstance(node, dict):
        return {}

    if "operator" in node:
        # Collect all tasks from left and right recursively
        tasks = []

        def collect_tasks(n):
            if isinstance(n, dict):
                if "task_id" in n and "operator" not in n:
                    # It's a leaf task
                    tasks.append(n)
                elif "operator" in n:
                    # Recursively collect from left and right
                    collect_tasks(n.get("left"))
                    collect_tasks(n.get("right"))

        collect_tasks(node.get("left"))
        collect_tasks(node.get("right"))

        # Return flattened structure
        return {
            "operator": node.get("operator", parent_operator),
            "children": tasks
        }
    else:
        # It's a task, return as-is
        return node.copy()


def count_tasks(node: Any) -> int:
    """Count total number of tasks in expression tree.

    Args:
        node: CttTask or CttOperatorNode

    Returns:
        Total count of leaf tasks
    """
    if not isinstance(node, dict):
        return 0

    if "operator" in node:
        # Operator node - count left and right
        left_count = count_tasks(node.get("left"))
        right_count = count_tasks(node.get("right"))
        return left_count + right_count
    else:
        # Task node
        return 1


def count_operators(node: Any) -> int:
    """Count total number of operators in expression tree.

    Args:
        node: CttTask or CttOperatorNode

    Returns:
        Total count of operator nodes
    """
    if not isinstance(node, dict):
        return 0

    if "operator" in node:
        # Operator node - count this one plus left and right
        left_count = count_operators(node.get("left"))
        right_count = count_operators(node.get("right"))
        return 1 + left_count + right_count
    else:
        # Task node
        return 0


def get_tree_depth(node: Any) -> int:
    """Get maximum depth of expression tree.

    Args:
        node: CttTask or CttOperatorNode

    Returns:
        Maximum depth (0 for leaf tasks, 1+ for operator nodes)
    """
    if not isinstance(node, dict):
        return 0

    if "operator" in node:
        left_depth = get_tree_depth(node.get("left"))
        right_depth = get_tree_depth(node.get("right"))
        return 1 + max(left_depth, right_depth)
    else:
        return 0


def get_operator_distribution(node: Any) -> dict[str, int]:
    """Get count of each operator type in expression tree.

    Args:
        node: CttTask or CttOperatorNode

    Returns:
        Dict mapping operator names to counts
    """
    distribution: dict[str, int] = {}

    def count_operators_by_type(n):
        if isinstance(n, dict):
            if "operator" in n:
                operator = n.get("operator", "unknown")
                distribution[operator] = distribution.get(operator, 0) + 1
                count_operators_by_type(n.get("left"))
                count_operators_by_type(n.get("right"))

    count_operators_by_type(node)
    return distribution


if __name__ == "__main__":
    # Example usage
    example_tree = {
        "operator": "sequence",
        "left": {
            "task_id": "get_details",
            "title": "Get Details",
            "task_description": "Get customer details"
        },
        "right": {
            "operator": "choice",
            "left": {
                "task_id": "cc_pay",
                "title": "Credit Card",
                "task_description": "CC payment"
            },
            "right": {
                "task_id": "paypal_pay",
                "title": "PayPal",
                "task_description": "PayPal payment"
            }
        }
    }

    print("=" * 60)
    print("ASCII ART VISUALIZATION")
    print("=" * 60)
    print(visualize_expression_tree(example_tree))

    print("\n" + "=" * 60)
    print("LINEAR NOTATION")
    print("=" * 60)
    print(linearize_expression_tree(example_tree))

    print("\n" + "=" * 60)
    print("TREE STATISTICS")
    print("=" * 60)
    print(f"Total tasks: {count_tasks(example_tree)}")
    print(f"Total operators: {count_operators(example_tree)}")
    print(f"Tree depth: {get_tree_depth(example_tree)}")
    print(f"Operator distribution: {get_operator_distribution(example_tree)}")

