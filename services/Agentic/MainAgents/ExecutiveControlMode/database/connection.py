import os
import sqlite3
from contextlib import contextmanager

# Resolve database file path relative to the ECN root
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ecn_agent.db"
)


@contextmanager
def _get_connection(db_path: str = DB_PATH):
    """Context manager that yields a configured SQLite connection."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize the SQLite tables matching modern agentic frameworks."""
    with _get_connection() as conn:
        cursor = conn.cursor()

        # 1. CrewAI & Hermes inspired Tasks table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                expected_output TEXT,
                assigned_agent TEXT,
                status TEXT CHECK(status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')) DEFAULT 'PENDING',
                final_output TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # 2. Dependency tracking for multi-agent workflows
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS task_dependencies (
                task_id TEXT,
                depends_on_task_id TEXT,
                PRIMARY KEY (task_id, depends_on_task_id),
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (depends_on_task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
            """
        )

        # 3. OpenCode execution trace model for detailed history log
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS task_execution_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                step_number INTEGER NOT NULL,
                node_name TEXT NOT NULL,
                action_type TEXT,
                inputs TEXT,
                outputs TEXT,
                duration_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
            """
        )

        # 4. Long-term / Semantic / Entity Memory Model
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                memory_type TEXT CHECK(memory_type IN ('LONG_TERM', 'SHORT_TERM', 'ENTITY')) DEFAULT 'LONG_TERM',
                task_context_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_context_id) REFERENCES tasks(id) ON DELETE SET NULL
            )
            """
        )

        # 5. KV active workspace store
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_context (
                task_id TEXT,
                key TEXT,
                value TEXT,
                PRIMARY KEY(task_id, key),
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
            """
        )

        # Trigger to auto-update updated_at timestamp on tasks update
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS update_task_timestamp 
            AFTER UPDATE ON tasks
            BEGIN
                UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = old.id;
            END;
            """
        )
