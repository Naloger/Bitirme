import json
from typing import Any

from services.Agentic.MainAgents.ExecutiveControlMode.database.connection import (
    _get_connection,
)


def log_execution_step(
    task_id: str,
    step_number: int,
    node_name: str,
    action_type: str,
    inputs: Any,
    outputs: Any,
    duration_ms: int | None = None,
) -> None:
    """Log a single step of the node execution cycle."""
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO task_execution_steps (task_id, step_number, node_name, action_type, inputs, outputs, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                step_number,
                node_name,
                action_type,
                json.dumps(inputs),
                json.dumps(outputs),
                duration_ms,
            ),
        )


def get_execution_steps(task_id: str) -> list[dict[str, Any]]:
    """Return all execution steps for a task as a list of dicts, ordered by step_number."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM task_execution_steps WHERE task_id = ? ORDER BY step_number",
            (task_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_task_statistics(task_id: str) -> dict[str, Any]:
    """Return aggregate statistics for a task."""
    with _get_connection() as conn:
        step_row = conn.execute(
            """
            SELECT
                COUNT(*)                       AS total_steps,
                COALESCE(SUM(duration_ms), 0)  AS total_duration_ms,
                COUNT(DISTINCT node_name)      AS unique_nodes_visited
            FROM task_execution_steps
            WHERE task_id = ?
            """,
            (task_id,),
        ).fetchone()

        mem_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM agent_memory WHERE task_context_id = ?",
            (task_id,),
        ).fetchone()

        status_row = conn.execute(
            "SELECT status FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        return {
            "total_steps": step_row["total_steps"],
            "total_duration_ms": step_row["total_duration_ms"],
            "unique_nodes_visited": step_row["unique_nodes_visited"],
            "memory_count": mem_row["cnt"],
            "current_status": status_row["status"] if status_row else None,
        }
