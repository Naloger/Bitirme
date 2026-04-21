"""Task-master Ollama LangGraph node.

- Reads prompt from state input_text
- Requests a CTT JSON task tree from Ollama
- Parses and validates CTT against Lib.CTT rules
- Returns normalized CTT payload in state output_text/ctt_state
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field

from langgraph.graph import END, START, StateGraph

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from Lib.CTT import CttTask, CttTreeState, validate_ctt_tree  # noqa: E402
from llm_config import ConfigError, load_llm_config  # noqa: E402


ALLOWED_CTT_OPERATORS = {
	"sequence",
	"choice",
	"interleaving",
	"order_independence",
	"suspend_resume",
	"disabling",
	"synchronization",
}


class TaskMasterState(BaseModel):
	"""State for task master node processing."""

	input_text: str = ""
	output_text: str = ""
	ctt_state: Dict[str, Any] = Field(default_factory=dict)
	validation_errors: List[str] = Field(default_factory=list)
	raw_response_text: str = ""
	model: str = ""


def _request_chat_once(base_url: str, payload: Dict[str, object], timeout_s: int) -> Dict[str, object]:
	data = json.dumps(payload).encode("utf-8")
	req = Request(
		f"{base_url.rstrip('/')}/api/chat",
		data=data,
		headers={"Content-Type": "application/json"},
		method="POST",
	)

	with urlopen(req, timeout=timeout_s) as response:
		body = response.read().decode("utf-8", errors="replace")
	parsed = json.loads(body)
	if not isinstance(parsed, dict):
		raise ValueError("Ollama response is not a JSON object.")
	return parsed


def _extract_content(response_obj: Dict[str, object]) -> str:
	message = response_obj.get("message")
	if isinstance(message, dict):
		content = str(message.get("content", "") or "")
		if content:
			return content
	content = str(response_obj.get("response", "") or "")
	return content


def _extract_json_text(text: str) -> str:
	fenced = re.search(r"```(?:json)?\s*({.*})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
	if fenced:
		return fenced.group(1).strip()

	start = text.find("{")
	end = text.rfind("}")
	if start != -1 and end != -1 and end > start:
		return text[start : end + 1].strip()

	return text.strip()


def _normalize_operator(value: Any) -> str | None:
	if value is None:
		return None
	operator = str(value).strip().lower()
	if operator in {"", "none", "null"}:
		return None
	if operator in ALLOWED_CTT_OPERATORS:
		return operator
	return None


def _coerce_task(obj: Dict[str, Any]) -> CttTask:
	task_id = str(obj["task_id"])
	title = str(obj["title"])
	task_description = str(obj["task_description"])

	task: CttTask = {
		"task_id": task_id,
		"title": title,
		"task_description": task_description,
	}

	if "status" in obj:
		task["status"] = str(obj["status"])  # type: ignore[assignment]
	if "optional" in obj:
		task["optional"] = bool(obj["optional"])
	if "iterative" in obj:
		task["iterative"] = bool(obj["iterative"])

	children: List[CttTask] = []
	children_raw = obj.get("children")
	if isinstance(children_raw, list):
		children = [_coerce_task(child) for child in children_raw if isinstance(child, dict)]
		task["children"] = children

	operator = _normalize_operator(obj.get("operator"))
	if len(children) >= 2:
		# Keep CTT valid when model emits missing/invalid operator for a branch node.
		task["operator"] = operator or "sequence"  # type: ignore[assignment]

	return task


def _parse_ctt_payload(text: str) -> Tuple[CttTreeState, List[str]]:
	json_text = _extract_json_text(text)
	payload = json.loads(json_text)
	if not isinstance(payload, dict):
		raise ValueError("CTT payload root must be an object.")

	raw_root_tasks = payload.get("root_tasks")
	if not isinstance(raw_root_tasks, list):
		raise ValueError("CTT payload must contain list field 'root_tasks'.")

	root_tasks: List[CttTask] = []
	for item in raw_root_tasks:
		if not isinstance(item, dict):
			raise ValueError("Each root task must be an object.")
		root_tasks.append(_coerce_task(item))

	ctt_state: CttTreeState = {"root_tasks": root_tasks}
	errors = validate_ctt_tree(root_tasks)
	return ctt_state, errors


def task_master_node(state: TaskMasterState) -> dict[str, Any]:
	"""LangGraph node that converts user input into CTT JSON."""

	if not state.input_text.strip():
		return {
			"output_text": "Input is empty.",
			"ctt_state": {},
			"validation_errors": ["Input is empty."],
		}

	try:
		cfg = load_llm_config()
	except (ConfigError, json.JSONDecodeError) as exc:
		return {
			"output_text": f"Config error: {exc}",
			"ctt_state": {},
			"validation_errors": [f"Config error: {exc}"],
		}

	if cfg.provider != "ollama":
		return {
			"output_text": "Only ollama provider is supported.",
			"ctt_state": {},
			"validation_errors": ["Only ollama provider is supported."],
		}

	try:
		ollama_cfg = cfg.raw["ollama"]
		model = state.model or str(ollama_cfg["model"])
		base_url = str(ollama_cfg["base_url"])
		timeout_seconds = int(ollama_cfg["timeout_seconds"])
		temperature = float(ollama_cfg["temperature"])
		num_ctx = int(ollama_cfg["num_ctx"])
	except (KeyError, TypeError, ValueError) as exc:
		return {
			"output_text": f"Config error: invalid or missing ollama settings ({exc}).",
			"ctt_state": {},
			"validation_errors": [f"Config error: {exc}"],
		}

	system_prompt = (
		"You are a ConcurTaskTrees (CTT) planner. "
		"Return ONLY valid JSON with this exact top-level schema: "
		"{\"root_tasks\": [CttTask, ...]}. "
		"Each task must include: task_id, title, task_description. "
		"Optional fields: status, operator, optional, iterative, children. "
		"Operator rules are strict: include operator ONLY when a task has 2 or more children, "
		"and omit operator when a task has 0 or 1 child. "
		"Allowed operator values: sequence, choice, interleaving, order_independence, "
		"suspend_resume, disabling, synchronization. "
		"Never output null, None, or empty string for operator; omit the key instead. "
		"If a task has 2+ children and relation is unclear, use operator=sequence. "
		"No markdown, no prose."
	)

	user_prompt = state.input_text.strip()

	payload: Dict[str, object] = {
		"model": model,
		"stream": False,
		"messages": [
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_prompt},
		],
		"options": {
			"temperature": temperature,
			"num_ctx": num_ctx,
		},
	}

	print(f"[START] Task master with model={model}", file=sys.stderr)
	print(f"[PROMPT] Input: {user_prompt[:120]}...", file=sys.stderr)

	response_text = ""
	try:
		response_obj = _request_chat_once(base_url=base_url, payload=payload, timeout_s=timeout_seconds)
		response_text = _extract_content(response_obj)
		ctt_state, validation_errors = _parse_ctt_payload(response_text)
	except (HTTPError, URLError, TimeoutError) as exc:
		return {
			"output_text": (
				f"Ollama request failed: {exc}\n\n"
				"Make sure Ollama is running:\n  ollama serve"
			),
			"ctt_state": {},
			"validation_errors": [f"Ollama request failed: {exc}"],
			"model": model,
		}
	except (ValueError, KeyError, json.JSONDecodeError) as exc:
		return {
			"output_text": f"CTT parse error: {exc}",
			"ctt_state": {},
			"validation_errors": [f"CTT parse error: {exc}"],
			"raw_response_text": response_text,
			"model": model,
		}

	output_text = json.dumps(ctt_state, ensure_ascii=True, indent=2)
	if validation_errors:
		output_text = (
			"CTT validation warnings:\n- "
			+ "\n- ".join(validation_errors)
			+ "\n\n"
			+ output_text
		)

	return {
		"output_text": output_text,
		"ctt_state": ctt_state,
		"validation_errors": validation_errors,
		"raw_response_text": response_text,
		"model": model,
	}


def create_task_master_graph() -> StateGraph[TaskMasterState]:
	"""Create and return task-master LangGraph."""

	graph = StateGraph(state_schema=TaskMasterState)
	graph.add_node("task_master", task_master_node)
	graph.add_edge(START, "task_master")
	graph.add_edge("task_master", END)
	return graph


if __name__ == "__main__":
	base = Path(__file__).parent
	input_path = base / "Input.txt"
	output_path = base / "Output.txt"

	if input_path.exists():
		test_prompt = input_path.read_text(encoding="utf-8").strip()
		result = task_master_node(TaskMasterState(input_text=test_prompt))

		output_lines = [
			"provider=ollama",
			f"model={result.get('model', '')}",
			f"validation_error_count={len(result.get('validation_errors', []))}",
			"",
			"[ctt_output]",
			result.get("output_text", ""),
			"",
			"[raw_response]",
			result.get("raw_response_text", ""),
		]
		output_path.write_text("\n".join(output_lines).strip() + "\n", encoding="utf-8")
		print(f"Task master node processed: {input_path} -> {output_path}")
	else:
		print(f"Input file not found: {input_path}")
