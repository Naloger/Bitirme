"""Task-master Ollama LangGraph node for converting user input into CTT JSON task trees."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field
from langgraph.graph import END, START, StateGraph

from Lib.CTT import CttTask, CttTreeState, validate_ctt_tree
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


def _extract_json_text(text: str) -> str:
    """Extract JSON object from text, handling code fences."""
    match = re.search(r"```(?:json)?\s*({.*})\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start:end + 1].strip()
    return text.strip()


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


def _coerce_task(obj: dict[str, Any]) -> CttTask:
    """Coerce raw task dict into validated CttTask."""
    task: CttTask = {
        "task_id": str(obj["task_id"]),
        "title": str(obj["title"]),
        "task_description": str(obj["task_description"]),
    }

    if "status" in obj:
        task["status"] = str(obj["status"])  # type: ignore[assignment]
    if "optional" in obj:
        task["optional"] = bool(obj["optional"])
    if "iterative" in obj:
        task["iterative"] = bool(obj["iterative"])
    elif _is_iteration_marker(obj.get("operator")):
        task["iterative"] = True

    children_raw = obj.get("children")
    if children_raw and isinstance(children_raw, list):
        children = [_coerce_task(c) for c in children_raw if isinstance(c, dict)]
        if children:
            task["children"] = children
            if len(children) >= 2:
                # Normalize operator from raw data
                raw_operator = obj.get("operator")
                operator = _normalize_operator(raw_operator)

                # Default to sequence if no valid operator provided for 2+ children
                if operator is None:
                    operator = "sequence"

                task["operator"] = operator  # type: ignore[assignment]

    return task


def _parse_ctt_payload(text: str) -> tuple[CttTreeState, list[str]]:
    """Parse and validate CTT JSON payload."""
    payload = json.loads(_extract_json_text(text))
    if not isinstance(payload, dict):
        raise ValueError("CTT payload root must be an object.")

    root_tasks_raw = payload.get("root_tasks")
    if not isinstance(root_tasks_raw, list):
        raise ValueError("CTT payload must contain 'root_tasks' list.")

    root_tasks: list[CttTask] = [_coerce_task(item) for item in root_tasks_raw if isinstance(item, dict)]
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
