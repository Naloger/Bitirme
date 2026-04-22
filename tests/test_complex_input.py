#!/usr/bin/env python
"""Test the task master node with complex input."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from Agents.Nodes.node_task_master.node_TaskMaster import task_master_node, TaskMasterState

input_path = Path(__file__).parent / "Agents/Nodes/node_task_master/Input.txt"
output_path = Path(__file__).parent / "Agents/Nodes/node_task_master/Output.txt"

if input_path.exists():
    test_input = input_path.read_text(encoding='utf-8').strip()
    print(f"Input length: {len(test_input)} chars\n")
    print(f"Input preview:\n{test_input[:200]}...\n")

    print("=" * 80)
    print("Running task master node with complex input...")
    print("=" * 80 + "\n")

    result = task_master_node(TaskMasterState(input_text=test_input))

    validation_errors = result.get("validation_errors", [])
    print(f"Validation errors: {len(validation_errors)}")
    if validation_errors:
        print("Errors:")
        for error in validation_errors:
            print(f"  - {error}")

    print(f"\nModel used: {result.get('model', 'unknown')}")
    print(f"\nOutput written to: {output_path}")
    print("\n✅ Task master execution complete!")
else:
    print(f"Input file not found: {input_path}")

