from typing import Any

from services.Agentic.MainAgents.ExecutiveControlMode.database.connection import (
    _get_connection,
)


def add_agent_memory(
    key: str,
    value: str,
    memory_type: str = "LONG_TERM",
    task_context_id: str | None = None,
) -> None:
    """Store a memory item (LONG_TERM, SHORT_TERM, or ENTITY)."""
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO agent_memory (key, value, memory_type, task_context_id)
            VALUES (?, ?, ?, ?)
            """,
            (key, value, memory_type, task_context_id),
        )


def get_agent_memories(
    memory_type: str = "LONG_TERM", task_context_id: str | None = None
) -> list[dict[str, Any]]:
    """Retrieve memories filtered by type or task context."""
    with _get_connection() as conn:
        if task_context_id:
            rows = conn.execute(
                "SELECT key, value, memory_type, created_at FROM agent_memory WHERE memory_type = ? AND task_context_id = ?",
                (memory_type, task_context_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT key, value, memory_type, created_at FROM agent_memory WHERE memory_type = ?",
                (memory_type,),
            ).fetchall()
        return [
            {
                "key": r["key"],
                "value": r["value"],
                "memory_type": r["memory_type"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
