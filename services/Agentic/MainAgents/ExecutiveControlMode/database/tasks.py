from typing import Any

from services.Agentic.MainAgents.ExecutiveControlMode.database.connection import (
    _get_connection,
)


def create_task(
    task_id: str,
    description: str,
    expected_output: str | None = None,
    assigned_agent: str | None = None,
) -> None:
    """Register a new task in the database."""
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO tasks (id, description, expected_output, assigned_agent, status)
            VALUES (?, ?, ?, ?, 'PENDING')
            ON CONFLICT(id) DO UPDATE SET 
                description=excluded.description, 
                expected_output=excluded.expected_output, 
                assigned_agent=excluded.assigned_agent
            """,
            (task_id, description, expected_output, assigned_agent),
        )


def update_task_status(
    task_id: str,
    status: str,
    final_output: str | None = None,
    error_message: str | None = None,
) -> None:
    """Update status, output, and errors of a task."""
    with _get_connection() as conn:
        conn.execute(
            """
            UPDATE tasks 
            SET status = ?, final_output = ?, error_message = ?
            WHERE id = ?
            """,
            (status, final_output, error_message, task_id),
        )


def add_task_dependency(task_id: str, depends_on_task_id: str) -> None:
    """Establish a dependency relationship between two tasks."""
    with _get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO task_dependencies (task_id, depends_on_task_id) VALUES (?, ?)",
            (task_id, depends_on_task_id),
        )


def get_task(task_id: str) -> dict[str, Any] | None:
    """Return the full task row as a dict, or None if not found."""
    with _get_connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None


def clear_task_data(task_id: str) -> None:
    """Clear memory logs, active contexts, and task rows associated with the task_id."""
    with _get_connection() as conn:
        conn.execute("DELETE FROM agent_context WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM agent_memory WHERE task_context_id = ?", (task_id,))
        conn.execute("DELETE FROM task_execution_steps WHERE task_id = ?", (task_id,))
        conn.execute(
            "DELETE FROM task_dependencies WHERE task_id = ? OR depends_on_task_id = ?",
            (task_id, task_id),
        )
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
