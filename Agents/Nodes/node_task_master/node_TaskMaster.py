"""Task-master Ollama LangGraph node for converting user input into CTT JSON task trees."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field
from langgraph.graph import END, START, StateGraph

from support_lib.CTT import CttTask, CttOperatorNode, CttTreeState, validate_ctt_tree
from llm_config import ConfigError, load_llm_config

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))



ALLOWED_CTT_OPERATORS = {"sequence", "choice", "interleaving", "disabling"}
ITERATION_MARKERS = {"*", "iteration", "iterative", "repeat", "loop"}

OPERATOR_ALIASES = {
    ">>": "sequence", "enabling": "sequence", "enable": "sequence",
    "sequential": "sequence", "pipeline": "sequence", "sequence": "sequence",
    "[]": "choice", "choice": "choice",
    "|": "interleaving", "||": "interleaving", "|||": "interleaving",
    "parallel": "interleaving", "concurrent": "interleaving", "interleaving": "interleaving",
    "[>": "disabling", "interruption": "disabling", "interrupt": "disabling", "disabling": "disabling",
}

SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.txt"
SYSTEM_PROMPT = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


class TaskMasterState(BaseModel):
    """State container for task master node processing."""
    input_text: str = ""
    output_text: str = ""
    ctt_state: dict[str, Any] = Field(default_factory=dict)
    validation_errors: list[str] = Field(default_factory=list)
    raw_response_text: str = ""
    model: str = ""


def _request_chat_once(base_url: str, payload: dict[str, Any], timeout_s: int) -> dict[str, Any]:
    """Send chat request to Ollama and parse JSON response."""
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=timeout_s) as response:
        parsed = json.loads(response.read().decode("utf-8", errors="replace"))

    if not isinstance(parsed, dict):
        raise ValueError("Ollama response is not a JSON object.")
    return parsed


def _extract_content(response_obj: dict[str, Any]) -> str:
    """Extract message content from Ollama response."""
    message = response_obj.get("message")
    if isinstance(message, dict):
        content = str(message.get("content", "") or "")
        if content:
            return content
    return str(response_obj.get("response", "") or "")


def _load_strict_json_object(text: str) -> dict[str, Any]:
    """Load a strict JSON object; reject fenced/prose/mixed output."""
    raw = text.strip()
    if not raw:
        raise ValueError("LLM output is empty.")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "LLM output must be raw valid JSON object only (no markdown/code fences/prose). "
            f"{exc}"
        ) from exc

    if not isinstance(parsed, dict):
        raise ValueError("CTT payload root must be a JSON object.")
    return parsed


def _require_non_empty_str(obj: dict[str, Any], key: str, context: str) -> str:
    """Require a non-empty string field in a strict parse context."""
    if key not in obj:
        raise ValueError(f"{context}: missing required field '{key}'.")
    value = obj[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}: field '{key}' must be a non-empty string.")
    return value.strip()


def _normalize_operator(value: Any) -> str | None:
    """Normalize and validate operator value."""
    if not value or (op := str(value).strip().lower()) in {"", "none", "null"}:
        return None
    canonical = OPERATOR_ALIASES.get(op, op)
    return canonical if canonical in ALLOWED_CTT_OPERATORS else None


def _is_iteration_marker(value: Any) -> bool:
    """Check if value indicates iteration."""
    if value is None:
        return False
    return str(value).strip().lower() in ITERATION_MARKERS


def _error_result(message: str, model: str = "", raw_response_text: str = "") -> dict[str, Any]:
    """Create standardized error result."""
    error_output: dict[str, Any] = {
        "output_text": message,
        "ctt_state": {},
        "validation_errors": [message],
    }
    if model:
        error_output["model"] = model
    if raw_response_text:
        error_output["raw_response_text"] = raw_response_text
    return error_output


def _coerce_operator_node(obj: dict[str, Any]) -> CttOperatorNode | None:
    """Try to coerce raw dict into CttOperatorNode (Expression Tree)."""
    if not isinstance(obj, dict) or "operator" not in obj:
        return None
    
    operator = _normalize_operator(obj.get("operator"))
    if not operator:
        return None
    
    left_raw = obj.get("left")
    right_raw = obj.get("right")
    
    if not left_raw or not right_raw:
        return None
    
    # Recursively coerce left and right children
    left = _coerce_node(left_raw)
    right = _coerce_node(right_raw)
    
    if not left or not right:
        return None
    
    res = {
        "operator": operator,
        "left": left,
        "right": right,
    }
    return cast(CttOperatorNode, cast(object, res))


def _coerce_node(obj: Any) -> CttTask | CttOperatorNode | None:
    """Coerce raw object into either CttTask or CttOperatorNode."""
    if not isinstance(obj, dict):
        return None
    
    # Try operator node first
    if "operator" in obj:
        op_node = _coerce_operator_node(obj)
        if op_node:
            return op_node
    
    # Otherwise try task
    if "task_id" in obj and "title" in obj and "task_description" in obj:
        return _coerce_task(obj)
    
    return None


def _coerce_task(obj: dict[str, Any], context: str = "task") -> CttTask:
    """Coerce raw task dict into validated CttTask."""
    task: CttTask = {
        "task_id": _require_non_empty_str(obj, "task_id", context),
        "title": _require_non_empty_str(obj, "title", context),
        "task_description": _require_non_empty_str(obj, "task_description", context),
    }

    if "status" in obj:
        status = obj["status"]
        if not isinstance(status, str) or not status.strip():
            raise ValueError(f"{context}: field 'status' must be a non-empty string.")
        task["status"] = status.strip()  # type: ignore[assignment]
    if "optional" in obj:
        if not isinstance(obj["optional"], bool):
            raise ValueError(f"{context}: field 'optional' must be boolean.")
        task["optional"] = obj["optional"]
    if "iterative" in obj:
        if not isinstance(obj["iterative"], bool):
            raise ValueError(f"{context}: field 'iterative' must be boolean.")
        task["iterative"] = obj["iterative"]

    # Support both old-style flat children and new-style expression tree
    
    # # Old-style: children as flat list with operator field
    # children_raw = obj.get("children")
    # if children_raw and isinstance(children_raw, list):
    #     children = [_coerce_task(c) for c in children_raw if isinstance(c, dict)]
    #     if children:
    #         task["children"] = children
    
    # New-style: children_tree as expression tree
    children_tree_raw = obj.get("children_tree")
    if children_tree_raw is not None:
        if not isinstance(children_tree_raw, list) or not children_tree_raw:
            raise ValueError(f"{context}: 'children_tree' must be a non-empty list when provided.")

        children_tree: list[CttTask | CttOperatorNode] = []
        for idx, node_raw in enumerate(children_tree_raw):
            coerced = _coerce_node(node_raw)
            if not coerced:
                raise ValueError(f"{context}: invalid children_tree node at index {idx}.")
            children_tree.append(coerced)
        task["children_tree"] = children_tree


    return task


def _parse_ctt_payload(text: str) -> tuple[CttTreeState, list[str]]:
    """Parse and validate CTT JSON payload."""
    payload = _load_strict_json_object(text)

    root_tasks_raw = payload.get("root_tasks")
    if not isinstance(root_tasks_raw, list) or not root_tasks_raw:
        raise ValueError("CTT payload must contain 'root_tasks' list.")

    root_tasks: list[CttTask] = []
    for idx, item in enumerate(root_tasks_raw):
        if not isinstance(item, dict):
            raise ValueError(f"root_tasks[{idx}] must be an object.")
        root_tasks.append(_coerce_task(item, context=f"root_tasks[{idx}]"))

    ctt_state: CttTreeState = {"root_tasks": root_tasks}
    errors = validate_ctt_tree(root_tasks)
    return ctt_state, errors


def task_master_node(state: TaskMasterState) -> dict[str, Any]:
    """Convert user input into CTT JSON via Ollama LLM."""
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
        model = state.model or str(ollama_cfg["model"])
        base_url = str(ollama_cfg["base_url"])
        timeout_s = int(ollama_cfg["timeout_seconds"])
        temp = float(ollama_cfg["temperature"])
        num_ctx = int(ollama_cfg["num_ctx"])
    except (KeyError, TypeError, ValueError) as exc:
        return _error_result(f"Config error: invalid ollama settings ({exc}).")
    
    payload: dict[str, Any] = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": state.input_text.strip()},
        ],
        "options": {"temperature": temp, "num_ctx": num_ctx},
    }
    
    print(f"[START] Task master with model={model}", file=sys.stderr)
    
    response_text: str = ""

    try:
        response_obj = _request_chat_once(base_url, payload, timeout_s)
        response_text = _extract_content(response_obj)
        ctt_state, validation_errors = _parse_ctt_payload(response_text)
    except (HTTPError, URLError, TimeoutError) as exc:
        return _error_result(f"Ollama request failed: {exc}\n\nEnsure Ollama is running: ollama serve", model=model)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        return _error_result(f"CTT parse error: {exc}", model=model, raw_response_text=response_text)
    
    output_text = json.dumps(ctt_state, ensure_ascii=True, indent=2)
    if validation_errors:
        output_text = f"CTT validation warnings:\n- {chr(10).join(validation_errors)}\n\n{output_text}"

    return {
        "output_text": output_text,
        "ctt_state": ctt_state,
        "validation_errors": validation_errors,
        "raw_response_text": response_text,
        "model": model,
    }


def create_task_master_graph() -> StateGraph[TaskMasterState]:
    """Create task-master LangGraph."""
    graph = StateGraph(state_schema=TaskMasterState)
    graph.add_node("task_master", task_master_node)
    graph.add_edge(START, "task_master")
    graph.add_edge("task_master", END)
    return graph


if __name__ == "__main__":
    input_path = Path(__file__).parent / "Input.txt"
    if input_path.exists():
        result = task_master_node(TaskMasterState(input_text=input_path.read_text(encoding="utf-8").strip()))
        output = "\n".join([
            f"provider=ollama",
            f"model={result.get('model', '')}",
            f"validation_error_count={len(result.get('validation_errors', []))}",
            "",
            "[ctt_output]",
            result.get("output_text", ""),
            "",
            "[raw_response]",
            result.get("raw_response_text", ""),
        ])
        (input_path.parent / "Output.txt").write_text(output + "\n", encoding="utf-8")
        print(f"Task master processed: {input_path} → Output.txt")
    else:
        print(f"Input file not found: {input_path}")
