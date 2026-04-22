"""Strict JSON parsing tests for task master CTT payload handling."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Agents.Nodes.node_task_master.node_TaskMaster import _parse_ctt_payload


def test_parse_accepts_raw_valid_json_only():
    payload = """
{
  "root_tasks": [
    {
      "task_id": "root",
      "title": "Root",
      "task_description": "Valid tree"
    }
  ]
}
""".strip()

    ctt_state, errors = _parse_ctt_payload(payload)

    assert ctt_state["root_tasks"][0]["task_id"] == "root"
    assert isinstance(errors, list)


def test_parse_rejects_code_fence_wrapped_json():
    payload = """
```json
{
  "root_tasks": [
    {
      "task_id": "root",
      "title": "Root",
      "task_description": "Valid tree"
    }
  ]
}
```
""".strip()

    try:
        _parse_ctt_payload(payload)
        assert False, "Expected ValueError for fenced JSON"
    except ValueError as exc:
        assert "raw valid JSON object only" in str(exc)


def test_parse_rejects_non_object_root_task_items():
    payload = """
{
  "root_tasks": [
    "not-an-object"
  ]
}
""".strip()

    try:
        _parse_ctt_payload(payload)
        assert False, "Expected ValueError for invalid root task entry"
    except ValueError as exc:
        assert "root_tasks[0] must be an object" in str(exc)


def test_parse_rejects_invalid_children_tree_nodes():
    payload = """
{
  "root_tasks": [
    {
      "task_id": "root",
      "title": "Root",
      "task_description": "Has invalid children_tree",
      "children_tree": [
        {
          "operator": "sequence",
          "left": {
            "task_id": "a",
            "title": "A",
            "task_description": "Left"
          }
        }
      ]
    }
  ]
}
""".strip()

    try:
        _parse_ctt_payload(payload)
        assert False, "Expected ValueError for invalid children_tree node"
    except ValueError as exc:
        assert "invalid children_tree node" in str(exc)

