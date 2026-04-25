from __future__ import annotations

from typing import Any, List, Set, Union

from typing_extensions import Literal, NotRequired, Required, TypeAlias, TypedDict

TaskStatus: TypeAlias = Literal[
    "pending",
    "running",
    "blocked",
    "done",
    "failed",
]

CttOperator: TypeAlias = Literal[
    "sequence",  # >>
    "choice",  # []
    "interleaving",  # |||
    "order_independence",  # |=|
    "suspend_resume",  # |>
    "disabling",  # [>
    "synchronization",  # |[]|
]


class CttTask(TypedDict):
    task_id: Required[str]
    title: Required[str]
    task_description: Required[str]
    status: NotRequired[TaskStatus]
    optional: NotRequired[bool]  # [T]
    iterative: NotRequired[bool]  # T*
    children_tree: NotRequired[List[Union["CttTask", "CttOperatorNode"]]]
    # Added for complexity scoring and decomposition
    complexity_score: NotRequired[float]  # 0..1
    decomposition_depth: NotRequired[int]  # recursion depth


class CttOperatorNode(TypedDict):
    operator: Required[CttOperator]
    left: Required[Union["CttTask", "CttOperatorNode"]]
    right: Required[Union["CttTask", "CttOperatorNode"]]


class CttTaskNode(TypedDict):
    task: Required[CttTask]


class CttTreeState(TypedDict):
    root_tasks: Required[List[CttTask]]


def validate_ctt_tree(root_tasks: List[CttTask]) -> List[str]:
    """Return CTT rule violations. Empty list means valid."""
    errors: List[str] = []
    seen_ids: Set[str] = set()

    def walk_task(task: CttTask, path: str) -> None:
        task_id = task["task_id"]
        task_path = f"{path}/{task_id}"

        if task_id in seen_ids:
            errors.append(f"Duplicate task_id: {task_id}")
            return
        seen_ids.add(task_id)

        children_tree = task.get("children_tree")
        if children_tree:
            for node in children_tree:
                walk_node(node, task_path)

    def walk_node(node: Any, path: str) -> None:
        if not isinstance(node, dict):
            return
        if "operator" in node:
            left = node.get("left")
            right = node.get("right")
            operator = node.get("operator")
            if left:
                walk_node(left, f"{path}/op({operator})")
            if right:
                walk_node(right, f"{path}/op({operator})")
        elif "task_id" in node:
            walk_task(node, path)  # type: ignore

    for root in root_tasks:
        walk_task(root, path="root")
    return errors


__all__ = [
    "TaskStatus",
    "CttOperator",
    "CttTask",
    "CttOperatorNode",
    "CttTaskNode",
    "CttTreeState",
    "validate_ctt_tree",
]
