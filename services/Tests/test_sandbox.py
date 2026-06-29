import os
import sys
import unittest

# Ensure the project root is in the path so we can import services
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from services.Agentic.MainAgents.ExecutiveControlMode.database import (
    clear_task_data,
    create_task,
    init_db,
)
from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlModels import ECNState
from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlNodes import task_executor
from services.CustomLibs.sandbox import sandbox


class TestSandboxEnvironment(unittest.TestCase):
    def test_run_python_success(self):
        """Test successful execution of Python code in Pyodide."""
        code = "print('Hello Pyodide!')"
        output = sandbox.run_python(code)

        self.assertIn("Hello Pyodide!", output)
        self.assertIn("exit code 0", output)

    def test_run_python_syntax_error(self):
        """Test Python syntax error capture in Pyodide."""
        code = "print('Unclosed string)"
        output = sandbox.run_python(code)

        self.assertIn("SyntaxError", output)

    def test_run_python_runtime_error(self):
        """Test Python runtime error capture in Pyodide."""
        code = "1 / 0"
        output = sandbox.run_python(code)

        self.assertIn("ZeroDivisionError", output)

    def test_run_shell_success(self):
        """Test successful execution of shell command."""
        # Using a universal command 'echo' which works in windows pwsh and cmd
        output = sandbox.run_shell("echo hello_world")
        self.assertIn("hello_world", output)
        self.assertIn("exit code 0", output)

    def test_run_shell_error(self):
        """Test execution of invalid shell command."""
        output = sandbox.run_shell("this_command_does_not_exist_123")
        self.assertNotEqual(
            output.find("exit code 1"), -1, "Should exit with non-zero code"
        )
        self.assertTrue(
            "STDERR" in output or "not recognized" in output or "not found" in output
        )


class TestToolParsingErrors(unittest.TestCase):
    def setUp(self):
        init_db()
        clear_task_data("test_id")
        create_task("test_id", "Test tool parsing", "Test output", "ECN Agent")
        self.base_state = ECNState(
            task_id="test_id",
            task="Test tool parsing",
            context={},
            reasoning="",
            execution_result={},
            evaluation_status="",
            reasoner_routing="requires_tool_execution",
            memory=[],
            iteration=1,
        )

    def test_invalid_json_format(self):
        """Test how the executor handles completely invalid JSON."""
        state = self.base_state.model_copy(
            update={"reasoning": "I will use a tool:\n{ this is not valid json"}
        )

        result = task_executor(state)
        output = result.execution_result["output"]
        self.assertIn("No JSON block found", output)

    def test_pydantic_missing_field(self):
        """Test how Pydantic handles a missing required field (e.g., missing 'code' for run_python)."""
        state = self.base_state.model_copy(
            update={"reasoning": '{"tool": "run_python", "args": {}}'}
        )

        result = task_executor(state)
        output = result.execution_result["output"]
        self.assertIn("Error parsing JSON tool call", output)

    def test_pydantic_invalid_tool_name(self):
        """Test how Pydantic handles an unknown tool name."""
        state = self.base_state.model_copy(
            update={"reasoning": '{"tool": "hack_mainframe", "args": {}}'}
        )

        result = task_executor(state)
        output = result.execution_result["output"]
        self.assertIn("Tool Execution Error", output)
        self.assertIn("Input should be", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
