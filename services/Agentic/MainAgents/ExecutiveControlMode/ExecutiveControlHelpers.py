from services.Agentic.MainAgents.ExecutiveControlMode.database import (
    clear_task_data,
    create_task,
    init_db,
    update_task_status,
)
from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlModels import (
    ECNState,
)


def default_initial_state(
    task_id: str,
    task: str,
    expected_output: str | None = None,
    assigned_agent: str = "ECN Agent",
) -> ECNState:
    """Return a fresh initial state for ECN, initializing SQLite records."""
    init_db()
    clear_task_data(task_id)

    create_task(
        task_id=task_id,
        description=task,
        expected_output=expected_output or "Task completion summary.",
        assigned_agent=assigned_agent,
    )
    update_task_status(task_id, "RUNNING")

    return ECNState(
        task_id=task_id,
        task=task,
        context={},
        reasoning="",
        execution_result={},
        evaluation_status="",
        reasoner_routing="",
        memory=[],
        iteration=0,
    )
