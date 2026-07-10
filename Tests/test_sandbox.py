import os
import sys
import unittest

# Ensure the project root is in the path so we can import services
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "../services", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from services.Agentic.MainAgents.ExecutiveControlMode.database import (
    clear_task_data,
    create_task,
    init_db,
)
from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlModels import (
    ECNState,
)
from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlNodes import (
    task_executor,
)
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

    def test_delete_file_success(self):
        """Test file deletion in sandbox."""
        sandbox.write_file("temp_to_delete.txt", "delete me")
        res = sandbox.delete_file("temp_to_delete.txt")
        self.assertIn("Successfully deleted", res)

    def test_search_grep_success(self):
        """Test search_grep function in sandbox."""
        sandbox.write_file("grep_test.txt", "this is a unique needle in a haystack")
        res = sandbox.search_grep("unique needle", "grep_test.txt")
        self.assertIn("grep_test.txt", res)
        self.assertIn("unique needle", res)
        sandbox.delete_file("grep_test.txt")

    def test_show_datetime(self):
        """Test show_datetime function in sandbox."""
        res = sandbox.show_datetime()
        self.assertIn("Current Date and Time", res)

    def test_get_env(self):
        """Test get_env function in sandbox."""
        res = sandbox.get_env()
        self.assertIn("OS:", res)
        self.assertIn("Python Version:", res)

    @unittest.mock.patch('requests.post')
    def test_web_search_success(self, mock_post):
        """Test web search command."""
        mock_response = unittest.mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <body>
        <table>
        <tr>
        <td><a rel="nofollow" href="https://example.com/python" class='result-link'>Python Title</a></td>
        </tr>
        <tr>
        <td class='result-snippet'>Python is nice.</td>
        </tr>
        </table>
        </body>
        </html>
        """
        mock_post.return_value = mock_response
        
        res = sandbox.web_search("python")
        self.assertIn("Python Title", res)
        self.assertIn("https://example.com/python", res)
        self.assertIn("Python is nice", res)

    @unittest.mock.patch('requests.get')
    def test_fetch_webpage_success(self, mock_get):
        """Test fetching a webpage and extracting text."""
        mock_response = unittest.mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><div>Hello World</div><script>var x=1;</script></body></html>"
        mock_get.return_value = mock_response
        
        res = sandbox.fetch_webpage("https://example.com")
        self.assertIn("Hello World", res)
        self.assertNotIn("var x=1", res)



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

    def test_json_parsing_with_whitespace(self):
        """Test parsing of JSON tool call with newlines and spaces between opening brace and 'tool' key."""
        reasoning = (
            "Thought: I want to search for leiden python example.\n"
            "ROUTE: web_search\n"
            "```json\n"
            "{\n"
            '  "tool": "web_search",\n'
            '  "args": {\n'
            '    "query": "python implementation of leiden algorithm example"\n'
            "  }\n"
            "}\n"
            "```"
        )
        state = self.base_state.model_copy(update={"reasoning": reasoning})
        
        # Patch SandboxEnv.web_search to return a mock response
        from unittest.mock import patch
        with patch("services.CustomLibs.sandbox.SandboxEnv.web_search") as mock_search:
            mock_search.return_value = "Mocked search result"
            result = task_executor(state)
            self.assertEqual(result.execution_result["output"], "Mocked search result")
            mock_search.assert_called_once_with("python implementation of leiden algorithm example")

    def test_flat_tool_call(self):
        """Test parsing of a flat tool call format like {"tool": "web_search", "query": "..."}"""
        reasoning = (
            "ROUTE: tool\n"
            "{\n"
            '  "tool": "web_search",\n'
            '  "query": "leiden community detection"\n'
            "}"
        )
        state = self.base_state.model_copy(update={"reasoning": reasoning})
        from unittest.mock import patch
        with patch("services.CustomLibs.sandbox.SandboxEnv.web_search") as mock_search:
            mock_search.return_value = "Mocked search result"
            result = task_executor(state)
            self.assertEqual(result.execution_result["output"], "Mocked search result")
            mock_search.assert_called_once_with("leiden community detection")

    def test_flat_arg_tool_call(self):
        """Test auto-healing of a completely flat argument call like {"query": "..."} without tool key"""
        reasoning = (
            "ROUTE: tool\n"
            "{\n"
            '  "query": "leiden community detection"\n'
            "}"
        )
        state = self.base_state.model_copy(update={"reasoning": reasoning})
        from unittest.mock import patch
        with patch("services.CustomLibs.sandbox.SandboxEnv.web_search") as mock_search:
            mock_search.return_value = "Mocked search result"
            result = task_executor(state)
            self.assertEqual(result.execution_result["output"], "Mocked search result")
            mock_search.assert_called_once_with("leiden community detection")


class TestTaskExecutorRouting(unittest.TestCase):
    def setUp(self):
        init_db()
        clear_task_data("test_id")
        create_task("test_id", "Test routing", "Test output", "ECN Agent")
        self.base_state = ECNState(
            task_id="test_id",
            task="Test routing",
            context={},
            reasoning="",
            execution_result={},
            evaluation_status="",
            reasoner_routing="requires_tool_execution",
            memory=[],
            iteration=1,
        )

    def test_route_show_datetime(self):
        state = self.base_state.model_copy(
            update={"reasoning": '{"tool": "show_datetime", "args": {}}'}
        )
        result = task_executor(state)
        output = result.execution_result["output"]
        self.assertIn("Current Date and Time", output)

    def test_route_get_env(self):
        state = self.base_state.model_copy(
            update={"reasoning": '{"tool": "get_env", "args": {}}'}
        )
        result = task_executor(state)
        output = result.execution_result["output"]
        self.assertIn("OS:", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
