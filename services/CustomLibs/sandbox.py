import os
import subprocess
import tempfile
import time

# Ensure we have a dedicated sandbox directory
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", ".."))
SANDBOX_DIR = os.path.join(_root, "sandbox_workspace")


class SandboxEnv:
    """
    A local sandbox environment for the agent to execute code and run shell commands.
    Provides basic isolation by restricting working directories and enforcing timeouts.
    """

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        if not os.path.exists(SANDBOX_DIR):
            os.makedirs(SANDBOX_DIR, exist_ok=True)

    @staticmethod
    def _sanitize_path(filename: str) -> str:
        """Prevent directory traversal attacks."""
        target = os.path.abspath(os.path.join(SANDBOX_DIR, filename))
        if not target.startswith(SANDBOX_DIR):
            raise ValueError(
                f"Access denied: Cannot access files outside sandbox ({filename})"
            )
        return target

    def write_file(self, filename: str, content: str) -> str:
        """Writes content to a file in the sandbox."""
        try:
            target_path = self._sanitize_path(filename)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {filename}"
        except (OSError, ValueError) as e:
            return f"Error writing file: {str(e)}"

    def read_file(self, filename: str) -> str:
        """Reads a file from the sandbox."""
        try:
            target_path = self._sanitize_path(filename)
            if not os.path.exists(target_path):
                return f"Error: File {filename} does not exist."
            with open(target_path, "r", encoding="utf-8") as f:
                return f.read()
        except (OSError, ValueError) as e:
            return f"Error reading file: {str(e)}"

    @staticmethod
    def list_files() -> str:
        """Lists all files in the sandbox workspace."""
        try:
            files = []
            for root, _, filenames in os.walk(SANDBOX_DIR):
                for filename in filenames:
                    rel_path = os.path.relpath(
                        os.path.join(root, filename), SANDBOX_DIR
                    )
                    files.append(rel_path)
            if not files:
                return "Workspace is empty."
            return "Files in workspace:\n" + "\n".join(f"- {f}" for f in files)
        except OSError as e:
            return f"Error listing files: {str(e)}"

    def run_python(self, code: str) -> str:
        """Executes Python code safely in a WebAssembly Sandbox using Pyodide (via Node.js) and returns stdout/stderr."""
        try:
            # Create a temporary file in the sandbox to hold the python code
            with tempfile.NamedTemporaryFile(
                dir=SANDBOX_DIR, suffix=".py", delete=False, mode="w", encoding="utf-8"
            ) as temp_file:
                temp_file.write(code)
                temp_path = temp_file.name

            # Create a JS runner script to bootstrap Pyodide
            js_code = f"""
const {{ loadPyodide }} = require("{os.path.join(_here, "../Libs/node_modules", "pyodide").replace(os.sep, "/")}");
const fs = require("fs");

async function main() {{
    try {{
        let pyodide = await loadPyodide();
        const code = fs.readFileSync("{temp_path.replace(os.sep, "/")}", "utf8");
        // Redirect stdout/stderr so we can capture it robustly
        pyodide.setStdout({{ batched: (msg) => console.log(msg) }});
        pyodide.setStderr({{ batched: (msg) => console.error(msg) }});
        
        let result = await pyodide.runPythonAsync(code);
        if (result !== undefined) {{
            console.log(result.toString());
        }}
    }} catch(err) {{
        console.error(err.toString());
        process.exit(1);
    }}
}}
main();
"""
            with tempfile.NamedTemporaryFile(
                dir=SANDBOX_DIR, suffix=".js", delete=False, mode="w", encoding="utf-8"
            ) as js_file:
                js_file.write(js_code)
                js_path = js_file.name

            t0 = time.perf_counter()
            # Execute via Node
            result = subprocess.run(
                ["node", js_path],
                cwd=SANDBOX_DIR,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            elapsed = time.perf_counter() - t0

            output = [
                f"Pyodide (WASM) Execution completed in {elapsed:.2f}s with exit code {result.returncode}"
            ]
            if result.stdout:
                output.extend(["--- STDOUT ---", result.stdout])
            if result.stderr:
                output.extend(["--- STDERR ---", result.stderr])

            return "\n".join(output)

        except subprocess.TimeoutExpired:
            return f"Error: Pyodide execution timed out after {self.timeout} seconds."
        except (OSError, subprocess.SubprocessError) as e:
            return f"Error executing Pyodide code: {str(e)}"
        finally:
            if "temp_path" in locals() and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            if "js_path" in locals() and os.path.exists(js_path):
                try:
                    os.remove(js_path)
                except OSError:
                    pass

    def run_shell(self, command: str) -> str:
        """Executes a generic shell command in the sandbox."""
        try:
            t0 = time.perf_counter()
            result = subprocess.run(
                command,
                cwd=SANDBOX_DIR,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            elapsed = time.perf_counter() - t0

            output = [
                f"Command completed in {elapsed:.2f}s with exit code {result.returncode}"
            ]
            if result.stdout:
                output.extend(["--- STDOUT ---", result.stdout])
            if result.stderr:
                output.extend(["--- STDERR ---", result.stderr])

            return "\n".join(output)

        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {self.timeout} seconds."
        except (OSError, subprocess.SubprocessError) as e:
            return f"Error executing shell command: {str(e)}"


# Singleton instance
sandbox = SandboxEnv()
