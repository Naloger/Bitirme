#!/usr/bin/env python3
"""Debug script to test task master node."""

from pathlib import Path
import sys
from Agents.Nodes.node_task_master.node_TaskMaster import (
    TaskMasterState,
    task_master_node,
)

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Read input
input_path = PROJECT_ROOT / "Agents/Nodes/node_task_master/Input.txt"
test_prompt = input_path.read_text(encoding="utf-8").strip()
print(f"Input length: {len(test_prompt)}")
print(f"Input preview: {test_prompt[:100]}...")

# Run node
result = task_master_node(TaskMasterState(input_text=test_prompt))
print("\n=== RESULT ===")
print(f"Output (first 300 chars):\n{result['output_text'][:300]}")
print(f"\nValidation errors: {result.get('validation_errors', [])}")
print(f"Model: {result.get('model', 'N/A')}")
