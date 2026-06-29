import json
from typing import Any

from services.Agentic.MainAgents.ExecutiveControlMode.database.connection import (
    _get_connection,
)


def save_context_val(task_id: str, key: str, val: Any) -> None:
    """Save a key-value context parameter to SQLite."""
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO agent_context (task_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(task_id, key) DO UPDATE SET value=excluded.value
            """,
            (task_id, key, json.dumps(val)),
        )


def get_all_context(task_id: str) -> dict[str, Any]:
    """Retrieve all context parameters for a given task from SQLite."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT key, value FROM agent_context WHERE task_id = ?", (task_id,)
        ).fetchall()
        return {row["key"]: json.loads(row["value"]) for row in rows}
