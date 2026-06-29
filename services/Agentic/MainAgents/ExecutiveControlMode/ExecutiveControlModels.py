from typing import Any, Literal, Union

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Pydantic Tooling Schemas
# ---------------------------------------------------------------------------


class RunPythonArgs(BaseModel):
    code: str = Field(description="The python code to execute in the sandbox.")


class RunShellArgs(BaseModel):
    command: str = Field(description="The shell command to execute in the sandbox.")


class WriteFileArgs(BaseModel):
    filename: str = Field(description="The path of the file to write.")
    content: str = Field(description="The content to write to the file.")


class ReadFileArgs(BaseModel):
    filename: str = Field(description="The path of the file to read.")


class ListFilesArgs(BaseModel):
    pass


class ToolCall(BaseModel):
    tool: Literal["run_python", "run_shell", "write_file", "read_file", "list_files"]
    args: Union[RunPythonArgs, RunShellArgs, WriteFileArgs, ReadFileArgs, ListFilesArgs]



# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class ECNState(BaseModel):
    """Shared state flowing through the Executive Control Network."""

    task_id: str
    task: str
    context: dict[str, Any]
    reasoning: str
    execution_result: dict[str, Any]
    evaluation_status: str  # "step_success", "step_error", "task_failed"
    reasoner_routing: str  # "requires_tool_execution", "task_completed"
    memory: list[str]
    iteration: int  # loop counter for max-iteration guard
