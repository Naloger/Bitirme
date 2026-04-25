"""Task-master using LangGraph's create_react_agent with CTT tool calling."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Literal, Optional, Union, cast

from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables.config import RunnableConfig
from pydantic import BaseModel, Field, ValidationError
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from support_lib.CTT import CttTask, CttOperatorNode, CttTreeState, validate_ctt_tree
from llm_config import ConfigError, load_llm_config

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Recursive Pydantic models for the tool's input schema
# ----------------------------------------------------------------------


class CttTaskModel(BaseModel):
    task_id: str = Field(..., description="Unique identifier of the task")
    title: str = Field(..., description="Short title of the task")
    task_description: str = Field(..., description="Detailed description of the task")
    status: Literal["pending", "running", "blocked", "done", "failed"] = "pending"
    complexity_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Normalized complexity score (0-1)")
    decomposition_depth: int = Field(default=0, description="Current recursion depth")
    optional: bool = False
    iterative: bool = False
    children_tree: Optional[list[Union["CttTaskModel", "CttOperatorNodeModel"]]] = None


class CttOperatorNodeModel(BaseModel):
    operator: Literal[
        "sequence",
        "choice",
        "interleaving",
        "order_independence",
        "suspend_resume",
        "disabling",
        "synchronization",
    ]
    left: Union["CttTaskModel", "CttOperatorNodeModel"]
    right: Union["CttTaskModel", "CttOperatorNodeModel"]


CttTaskModel.model_rebuild()
CttOperatorNodeModel.model_rebuild()


class CttRoot(BaseModel):
    root_tasks: list[CttTaskModel] = Field(..., description="Top-level CTT tasks")


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------


def _parse_nested_string(input_data: Any) -> Any:
    """Recursively parse stringified JSON in nested objects."""
    max_depth = 5

    def parse_recursive(obj: Any, depth: int = 0) -> Any:
        if depth > max_depth:
            return obj
        if isinstance(obj, str):
            try:
                parsed = json.loads(obj)
                if isinstance(parsed, (dict, list)):
                    return parse_recursive(parsed, depth + 1)
                return parsed
            except (json.JSONDecodeError, TypeError):
                if obj.startswith("[") or obj.startswith("{"):
                    try:
                        return json.loads(obj)
                    except (json.JSONDecodeError, TypeError):
                        return obj
                return obj
        elif isinstance(obj, dict):
            return {k: parse_recursive(v, depth + 1) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [parse_recursive(item, depth + 1) for item in obj]
        return obj

    return parse_recursive(input_data)


def visualize_ctt_tree(ctt_state: CttTreeState, max_depth: int = 3) -> str:
    """Generate a text-based visualization of the CTT tree."""
    lines = ["=" * 60, "CTT TREE VISUALIZATION", "=" * 60, ""]

    def render_node(node: Any, depth: int = 0, is_last: bool = True) -> None:
        if depth > max_depth:
            return

        indent = "  " * depth
        connector = "└── " if is_last else "├── "

        if isinstance(node, dict) and "operator" in node:
            op = node.get("operator", "unknown").upper()
            lines.append(f"{indent}[{op}]")
            if "left" in node:
                render_node(node["left"], depth + 1, False)
            if "right" in node:
                render_node(node["right"], depth + 1, True)
        elif isinstance(node, dict):
            task_obj = node
            status_icon = {
                "pending": "○",
                "running": "◐",
                "blocked": "◌",
                "done": "●",
                "failed": "✗",
            }.get(task_obj.get("status", "pending"), "○")
            optional_tag = " [OPT]" if task_obj.get("optional") else ""
            iterative_tag = " [LOOP]" if task_obj.get("iterative") else ""
            cs = task_obj.get("complexity_score", "?")
            lines.append(
                f"{indent}{connector}[{status_icon}] {task_obj.get('title', 'Untitled')}{optional_tag}{iterative_tag} (c={cs})"
            )
            lines.append(f"{indent}    ID: {task_obj.get('task_id', 'N/A')}")
            desc = task_obj.get("task_description", "No description")
            lines.append(
                f"{indent}    Desc: {desc[:60]}..."
                if len(desc) > 60
                else f"{indent}    Desc: {desc}"
            )

            children = task_obj.get("children_tree", [])
            if children:
                lines.append(f"{indent}    Children ({len(children)}):")
                for child_idx, child in enumerate(children):
                    is_last_child = child_idx == len(children) - 1
                    render_node(child, depth + 1, is_last_child)

    for idx, task in enumerate(ctt_state.get("root_tasks", [])):
        is_last_root = idx == len(ctt_state.get("root_tasks", [])) - 1
        lines.append(f"Task {idx + 1}/{len(ctt_state.get('root_tasks', []))}:")
        render_node(task, 0, is_last_root)
        lines.append("")

    lines.append("=" * 60)
    lines.append(f"Total root tasks: {len(ctt_state.get('root_tasks', []))}")
    lines.append("=" * 60)

    return "\n".join(lines)


def _convert_task(py_task: CttTaskModel) -> CttTask:
    task: CttTask = {
        "task_id": py_task.task_id,
        "title": py_task.title,
        "task_description": py_task.task_description,
        "status": py_task.status,
        "optional": py_task.optional,
        "iterative": py_task.iterative,
    }
    # Add optional fields if present
    if py_task.complexity_score is not None:
        task["complexity_score"] = py_task.complexity_score
    if py_task.decomposition_depth != 0:
        task["decomposition_depth"] = py_task.decomposition_depth

    if py_task.children_tree:
        children = []
        for child in py_task.children_tree:
            if isinstance(child, CttTaskModel):
                children.append(_convert_task(child))
            else:
                children.append(_convert_operator(child))
        task["children_tree"] = children
    return task


def _convert_operator(py_op: CttOperatorNodeModel) -> CttOperatorNode:
    left = (
        _convert_task(py_op.left)
        if isinstance(py_op.left, CttTaskModel)
        else _convert_operator(py_op.left)
    )
    right = (
        _convert_task(py_op.right)
        if isinstance(py_op.right, CttTaskModel)
        else _convert_operator(py_op.right)
    )
    return {"operator": py_op.operator, "left": left, "right": right}


# ----------------------------------------------------------------------
# Complexity scoring heuristics
# ----------------------------------------------------------------------

def compute_complexity_from_task(task: CttTask) -> float:
    """
    Heuristic complexity score (0..1) based on multiple factors:
    - Description length (words and characters, capped)
    - Number of direct children (if any)
    """
    # If the model already assigned a score, trust it
    if "complexity_score" in task and task["complexity_score"] is not None:
        return float(task["complexity_score"])

    score = 0.0
    weights = {
        "description": 0.35,   # up to 0.35
        "children": 0.30,      # up to 0.30
        "depth": 0.15,         # up to 0.15
    }

    # 1. Description complexity (word count + character length)
    desc = task.get("task_description", "")
    word_count = len(desc.split())
    char_count = len(desc)
    # Normalize: 0 at 0 words, 1 at 200+ words (capped)
    desc_score = min(word_count / 50.0, 0.5) + min(char_count / 200.0, 0.2)
    desc_score = min(desc_score, 1.0)  # overall description factor
    score += weights["description"] * desc_score

    # 2. Children count (more children = more coordination complexity)
    children = task.get("children_tree", [])
    if children:
        # Up to 10 children gives full weight, logarithmic scaling
        child_score = min(len(children) / 10.0, 1.0)
        # Bonus if any child is optional/iterative – we'll let recursion handle that, so no extra here
        score += weights["children"] * child_score

    return min(max(score, 0.0), 1.0)


def update_complexity_scores(tree: list[CttTask]) -> None:
    """Recursively compute and store complexity_score for every task."""
    def recurse(node: Union[CttTask, CttOperatorNode]) -> None:
        if "operator" in node:
            recurse(node["left"])
            recurse(node["right"])
        else:
            task = cast(CttTask, node)   # explicit cast to CttTask
            task["complexity_score"] = compute_complexity_from_task(task)
            if "children_tree" in task:
                for child in task["children_tree"]:
                    recurse(child)
    for root in tree:
        recurse(root)


# ----------------------------------------------------------------------
# Recursive decomposition and iterative refinement
# ----------------------------------------------------------------------

def should_decompose(task: CttTask, current_depth: int, max_depth: int, threshold: float) -> bool:
    """Decide whether a task needs to be broken down further."""
    if current_depth >= max_depth:
        return False
    complexity = task.get("complexity_score")
    if complexity is None:
        complexity = 1.0
    children = task.get("children_tree", [])
    return complexity > threshold and len(children) == 0

def call_decomposition_agent(
    task_title: str,
    task_description: str,
    model_name: str,
    base_url: str,
    temperature: float,
    num_ctx: int,
) -> Optional[list[CttTask]]:
    """
    Invoke the same CTT agent to break a single task into a subtree.
    Returns a list of child tasks (possibly wrapped in operators) or None on failure.
    """
    # Stronger prompt with explicit schema example
    prompt = f"""You are a CTT expert. Decompose the following task into a structured CTT subtree.
Task title: {task_title}
Task description: {task_description}

The output MUST be a valid JSON object conforming exactly to this schema:
{{
  "root_tasks": [
    {{
      "task_id": "unique_id",
      "title": "subtask title",
      "task_description": "detailed description of this subtask",
      "optional": false,
      "iterative": false,
      "children_tree": [ ... ]   // optional, for further decomposition
    }}
  ]
}}

If you need to use operators, use the same structure but wrap with operator nodes.
IMPORTANT: Every task MUST include "task_id", "title", "task_description". Do not omit task_description.
Return ONLY the JSON, no extra text.
"""
    llm = init_chat_model(
        model=f"ollama:{model_name}",
        temperature=temperature,
        num_ctx=num_ctx,
        base_url=base_url,
    )
    agent = create_agent(
        model=llm,
        tools=[create_ctt_tree],
        system_prompt="You are an expert in CTT. Always respond using the create_ctt_tree tool with valid JSON.",
        checkpointer=MemorySaver(),
    )
    config: RunnableConfig = {"configurable": {"thread_id": f"decomp_{task_title}"}}
    try:
        response = agent.invoke({"messages": [HumanMessage(content=prompt)]}, config=config)
        if not response or not response.get("messages"):
            return None
        tool_calls = []
        for msg in reversed(response["messages"]):
            if isinstance(msg, AIMessage) and msg.tool_calls:
                tool_calls = list(msg.tool_calls)
                break
        if not tool_calls or tool_calls[0]["name"] != "create_ctt_tree":
            # Fallback: try to parse the last message content as JSON
            last_msg = response["messages"][-1]
            if hasattr(last_msg, "content") and last_msg.content:
                content = last_msg.content
                # Extract JSON block
                import re
                json_match = re.search(r'\{.*}|\[.*]', content, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        if "root_tasks" in parsed:
                            args = parsed
                        else:
                            args = {"root_tasks": [parsed] if isinstance(parsed, dict) else parsed}
                        # Manually validate and repair missing task_description
                        args = _repair_missing_task_description(args)
                        validated = CttRoot.model_validate(args)
                        children_list = []
                        for rt in validated.root_tasks:
                            conv = _convert_task(rt)
                            if "children_tree" in conv:
                                children_list.extend(conv["children_tree"])
                            else:
                                children_list.append(conv)
                        return children_list
                    except (json.JSONDecodeError, ValidationError):
                        pass
            return None
        args = tool_calls[0]["args"]
        if isinstance(args, str):
            args = _parse_nested_string(json.loads(args))
        else:
            args = _parse_nested_string(args)
        # Repair missing task_description fields
        args = _repair_missing_task_description(args)
        if "root_tasks" not in args:
            if "task_id" in args:
                args = {"root_tasks": [args]}
            else:
                return None
        validated = CttRoot.model_validate(args)
        children_list = []
        for rt in validated.root_tasks:
            conv = _convert_task(rt)
            if "children_tree" in conv:
                children_list.extend(conv["children_tree"])
            else:
                children_list.append(conv)
        return children_list
    except (json.JSONDecodeError, KeyError, TypeError, ValidationError) as e:
        logger.warning(f"Decomposition agent error: {e}")
        return None

def _repair_missing_task_description(args: dict) -> dict:
    """Recursively add default task_description if missing."""
    if "root_tasks" in args:
        for task in args["root_tasks"]:
            _repair_task(task)
    elif "task_id" in args:
        _repair_task(args)
    return args

def _repair_task(task: dict) -> None:
    if "task_description" not in task or not task["task_description"]:
        task["task_description"] = f"Subtask of {task.get('title', task.get('task_id', 'unnamed'))}"
    if "children_tree" in task:
        for child in task["children_tree"]:
            if "operator" in child:
                if "left" in child:
                    _repair_task(child["left"] if isinstance(child["left"], dict) else {})
                if "right" in child:
                    _repair_task(child["right"] if isinstance(child["right"], dict) else {})
            else:
                _repair_task(child)

def refine_tree(
    root_tasks: list[CttTask],
    model_name: str,
    base_url: str,
    temperature: float,
    num_ctx: int,
    max_depth: int = 3,
    complexity_threshold: float = 0.7,
    max_iterations: int = 5,
) -> list[CttTask]:
    """
    Iteratively decompose tasks that are too complex.
    Returns a new tree with decomposition_depth incremented where needed.
    """
    update_complexity_scores(root_tasks)

    def process_node(
        node: Union[CttTask, CttOperatorNode], current_depth: int
    ) -> Union[CttTask, CttOperatorNode]:
        if "operator" in node:
            # Process children inside operator
            left_node = process_node(node["left"], current_depth)
            right_node = process_node(node["right"], current_depth)
            new_node: CttOperatorNode = node.copy()  # type: ignore
            new_node["left"] = left_node
            new_node["right"] = right_node
            return new_node
        else:
            # Task node
            task = cast(CttTask, cast(object, node.copy()))
            if should_decompose(task, current_depth, max_depth, complexity_threshold):
                children = call_decomposition_agent(
                    task_title=task.get("title", "Untitled"),
                    task_description=task.get("task_description", ""),
                    model_name=model_name,
                    base_url=base_url,
                    temperature=temperature,
                    num_ctx=num_ctx,
                )
                if children is not None:
                    task["children_tree"] = children
                    task["decomposition_depth"] = current_depth + 1
                    # Process new children
                    processed_children = []
                    for child in task["children_tree"]:
                        processed_children.append(process_node(child, current_depth + 1))
                    task["children_tree"] = processed_children
                    task["complexity_score"] = compute_complexity_from_task(task)
            # Process existing children
            if "children_tree" in task and task["children_tree"]:
                new_children = []
                for child in task["children_tree"]:
                    new_children.append(process_node(child, current_depth + 1))
                task["children_tree"] = new_children
            return task

    iteration = 0
    changed = True
    current_trees = root_tasks
    while changed and iteration < max_iterations:
        changed = False
        new_trees = []
        for root in current_trees:
            processed = process_node(root, 0)
            new_trees.append(cast(CttTask, processed))
        update_complexity_scores(new_trees)

        def needs_more(task: Union[CttTask, CttOperatorNode]) -> bool:
            if "operator" in task:
                return needs_more(task["left"]) or needs_more(task["right"])
            else:
                score = task.get("complexity_score")
                if score is None:
                    score = 1.0
                return (
                    score > complexity_threshold
                    and len(task.get("children_tree", [])) == 0
                )
        if any(needs_more(t) for t in new_trees):
            changed = True
        current_trees = new_trees
        iteration += 1

    return current_trees


# ----------------------------------------------------------------------
# Tool definition
# ----------------------------------------------------------------------
@tool(args_schema=CttRoot, name_or_callable="create_ctt_tree")
def create_ctt_tree(root_tasks: list[CttTaskModel]) -> str:
    """Create a CTT tree from the user's description."""
    return f"CTT tree created with {len(root_tasks)} root tasks."


# ----------------------------------------------------------------------
# State schema (with added refinement parameters)
# ----------------------------------------------------------------------
class TaskMasterState(BaseModel):
    input_text: str = ""
    output_text: str = ""
    ctt_state: CttTreeState = Field(default_factory=lambda: {"root_tasks": []})
    validation_errors: list[str] = Field(default_factory=list)
    raw_response_text: str = ""
    model: str = ""
    # Refinement control parameters
    max_depth: int = 3
    complexity_threshold: float = 0.7
    max_iterations: int = 5


# ----------------------------------------------------------------------
# Error helper
# ----------------------------------------------------------------------
def _error_result(
    message: str, model: str = "", raw_response_text: str = ""
) -> dict[str, Any]:
    return {
        "output_text": message,
        "ctt_state": {"root_tasks": []},
        "validation_errors": [message],
        "model": model,
        "raw_response_text": raw_response_text,
        "visualization": "",
    }


# ----------------------------------------------------------------------
# Main node function (includes refinement)
# ----------------------------------------------------------------------
def task_master_node(state: TaskMasterState) -> dict[str, Any]:
    """Convert user input into CTT using a LangGraph ReAct agent and then refine it."""
    if not state.input_text.strip():
        return _error_result("Input is empty.")

    try:
        cfg = load_llm_config()
    except (ConfigError, json.JSONDecodeError) as exc:
        return _error_result(f"Config error: {exc}")

    if cfg.provider != "ollama":
        return _error_result("Only ollama provider is supported.")

    try:
        ollama_cfg = cfg.raw["ollama"]
        model_name = state.model or str(ollama_cfg["model"])
        temperature = float(ollama_cfg.get("temperature", 0.7))
        num_ctx = int(ollama_cfg.get("num_ctx", 4096))
        base_url = str(ollama_cfg.get("base_url", "http://localhost:11434"))
    except (KeyError, TypeError, ValueError) as exc:
        return _error_result(f"Config error: invalid ollama settings ({exc}).")

    system_message = (
        "You are an expert in CTT (Concurrent Task Trees). "
        "Use the 'create_ctt_tree' tool to represent the user's task description. "
        "The tool expects a list of root tasks. Each task can have nested children (subtasks or operators). "
        "Operators must be one of: sequence, choice, interleaving, order_independence, suspend_resume, disabling, synchronization. "
        "You can use common aliases like '>>' for sequence, '[]' for choice, '||' for interleaving etc. – the tool will normalise them. "
        "If the user asks for a tree, always respond by calling the tool."
    )

    llm = init_chat_model(
        model=f"ollama:{model_name}",
        temperature=temperature,
        num_ctx=num_ctx,
        base_url=base_url,
    )

    agent = create_agent(
        model=llm,
        tools=[create_ctt_tree],
        system_prompt=system_message,
        checkpointer=MemorySaver(),
    )

    config: RunnableConfig = {"configurable": {"thread_id": "1"}}
    max_retries = 2
    agent_output = None

    for attempt in range(max_retries + 1):
        try:
            agent_output = agent.invoke(
                {"messages": [HumanMessage(content=state.input_text.strip())]},
                config=config,
            )
            break
        except Exception as exc:
            if attempt < max_retries and "peer closed connection" in str(exc).lower():
                time.sleep(1)
                continue
            return _error_result(
                f"Ollama connection error: {exc}\n\nEnsure Ollama is running: ollama serve",
                model=model_name,
            )

    if not agent_output or not agent_output.get("messages"):
        return _error_result("Agent returned empty response.", model=model_name)

    tool_calls: list[Any] = []
    for msg in reversed(agent_output["messages"]):
        if isinstance(msg, AIMessage) and msg.tool_calls:
            tool_calls = list(msg.tool_calls)
            break

    if not tool_calls:
        return _error_result("No tool calls found.", model=model_name)

    tool_call = tool_calls[0]
    if tool_call["name"] != "create_ctt_tree":
        return _error_result(
            f"Unexpected tool call: {tool_call['name']}. Expected 'create_ctt_tree'.",
            model=model_name,
            raw_response_text=str(tool_call),
        )

    args = tool_call["args"]
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            pass
    args = _parse_nested_string(args)
    if "root_tasks" not in args and "task_id" in args:
        args = {"root_tasks": [args]}

    raw_json = json.dumps(args, indent=2)

    try:
        validated_root = CttRoot.model_validate(args)
    except ValidationError as e:
        return _error_result(
            f"Schema validation error: {e}",
            model=model_name,
            raw_response_text=raw_json,
        )

    converted_root_tasks = [_convert_task(task) for task in validated_root.root_tasks]
    ctt_state: CttTreeState = {"root_tasks": converted_root_tasks}

    # Refinement stage
    refined_tasks = refine_tree(
        root_tasks=converted_root_tasks,
        model_name=model_name,
        base_url=base_url,
        temperature=temperature,
        num_ctx=num_ctx,
        max_depth=state.max_depth,
        complexity_threshold=state.complexity_threshold,
        max_iterations=state.max_iterations,
    )
    ctt_state["root_tasks"] = refined_tasks

    validation_errors = validate_ctt_tree(refined_tasks)

    output_text = json.dumps(ctt_state, ensure_ascii=True, indent=2)
    if validation_errors:
        output_text = (
            "CTT validation warnings:\n- "
            + "\n- ".join(validation_errors)
            + f"\n\n{output_text}"
        )

    visualization = visualize_ctt_tree(ctt_state)

    return {
        "output_text": output_text,
        "ctt_state": ctt_state,
        "validation_errors": validation_errors,
        "raw_response_text": raw_json,
        "model": model_name,
        "visualization": visualization,
    }


# ----------------------------------------------------------------------
# Graph builder
# ----------------------------------------------------------------------
def create_task_master_graph():
    from langgraph.graph import StateGraph, START, END

    graph = StateGraph(TaskMasterState)
    graph.add_node("task_master", task_master_node)
    graph.add_edge(START, "task_master")
    graph.add_edge("task_master", END)
    return graph.compile()


# ----------------------------------------------------------------------
# Standalone execution
# ----------------------------------------------------------------------
if __name__ == "__main__":
    input_path = Path(__file__).parent / "Input.txt"
    if input_path.exists():
        result = task_master_node(
            TaskMasterState(input_text=input_path.read_text(encoding="utf-8").strip())
        )
        output_lines = [
            "provider=ollama",
            f"model={result.get('model', '')}",
            f"validation_error_count={len(result.get('validation_errors', []))}",
            "",
            "[ctt_output]",
            result.get("output_text", ""),
            "",
            "[visualization]",
            visualize_ctt_tree(result.get("ctt_state", {"root_tasks": []})),
            "",
            "[raw_response]",
            result.get("raw_response_text", ""),
        ]
        (input_path.parent / "Output.txt").write_text(
            "\n".join(output_lines) + "\n", encoding="utf-8"
        )
        print(f"Task master processed: {input_path} → Output.txt")
    else:
        print(f"Input file not found: {input_path}")