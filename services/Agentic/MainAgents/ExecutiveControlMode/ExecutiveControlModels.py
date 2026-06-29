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


class WebSearchArgs(BaseModel):
    query: str = Field(description="The search query to search the web for.")


class FetchWebpageArgs(BaseModel):
    url: str = Field(description="The URL of the webpage to fetch.")


class SearchGrepArgs(BaseModel):
    query: str = Field(description="The text or regex query to search for within workspace files.")
    file_pattern: str = Field(default="*", description="Optional glob pattern to filter files (e.g. '*.py').")


class DeleteFileArgs(BaseModel):
    filename: str = Field(description="The path of the file to delete.")


class ShowDatetimeArgs(BaseModel):
    pass


class GetEnvArgs(BaseModel):
    pass


class ToolCall(BaseModel):
    tool: Literal[
        "run_python",
        "run_shell",
        "write_file",
        "read_file",
        "list_files",
        "web_search",
        "fetch_webpage",
        "search_grep",
        "delete_file",
        "show_datetime",
        "get_env"
    ]
    args: Union[
        RunPythonArgs,
        RunShellArgs,
        WriteFileArgs,
        ReadFileArgs,
        ListFilesArgs,
        WebSearchArgs,
        FetchWebpageArgs,
        SearchGrepArgs,
        DeleteFileArgs,
        ShowDatetimeArgs,
        GetEnvArgs
    ]



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
    # graph_memory: list[tuple[str, str,str]]
    iteration: int  # loop counter for max-iteration guard
