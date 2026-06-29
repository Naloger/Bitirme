import os
import re
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

    def delete_file(self, filename: str) -> str:
        """Deletes a file from the sandbox."""
        try:
            target_path = self._sanitize_path(filename)
            if not os.path.exists(target_path):
                return f"Error: File {filename} does not exist."
            if os.path.isdir(target_path):
                return f"Error: {filename} is a directory. Cannot delete directory with this tool."
            os.remove(target_path)
            return f"Successfully deleted file {filename}"
        except (OSError, ValueError) as e:
            return f"Error deleting file: {str(e)}"

    def search_grep(self, query: str, file_pattern: str = "*") -> str:
        """Searches for a string or regex pattern in the sandbox files."""
        import fnmatch
        try:
            results = []
            compiled_query = re.compile(query, re.IGNORECASE)
            
            for root, _, filenames in os.walk(SANDBOX_DIR):
                for filename in fnmatch.filter(filenames, file_pattern):
                    filepath = os.path.join(root, filename)
                    rel_path = os.path.relpath(filepath, SANDBOX_DIR)
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            for idx, line in enumerate(f, 1):
                                if compiled_query.search(line):
                                    results.append(f"{rel_path}:{idx}: {line.strip()}")
                    except OSError:
                        pass
            if not results:
                return f"No matches found for '{query}'"
            return "\n".join(results[:100])
        except Exception as e:
            return f"Error executing search_grep: {str(e)}"

    def web_search(self, query: str) -> str:
        """Performs a web search using DuckDuckGo Lite and returns titles, URLs, and snippets."""
        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            r = requests.post(
                "https://lite.duckduckgo.com/lite/",
                data={"q": query},
                headers=headers,
                timeout=10
            )
            r.raise_for_status()
            
            link_matches = re.findall(
                r"<a[^>]+href=\"([^\"]+)\"[^>]*class='result-link'[^>]*>(.*?)</a>",
                r.text,
                re.DOTALL
            )
            snippet_matches = re.findall(
                r"class='result-snippet'[^>]*>(.*?)</td>",
                r.text,
                re.DOTALL
            )
            
            results = []
            for i in range(min(8, len(link_matches))):
                url, title = link_matches[i]
                title = re.sub(r"<[^>]+>", "", title).strip()
                title = (title.replace('&quot;', '"')
                             .replace('&#x27;', "'")
                             .replace('&amp;', '&')
                             .replace('&gt;', '>')
                             .replace('&lt;', '<'))
                snippet = ""
                if i < len(snippet_matches):
                    snippet = re.sub(r"<[^>]+>", "", snippet_matches[i]).strip()
                    snippet = (snippet.replace('&quot;', '"')
                                      .replace('&#x27;', "'")
                                      .replace('&amp;', '&')
                                      .replace('&gt;', '>')
                                      .replace('&lt;', '<')
                                      .replace('&nbsp;', ' '))
                results.append(f"Title: {title}\nURL: {url}\nSnippet: {snippet}\n")
                
            if not results:
                return "No search results found."
            return "\n".join(results)
        except Exception as e:
            return f"Error executing web_search: {str(e)}"

    def fetch_webpage(self, url: str) -> str:
        """Downloads a webpage and strips HTML tags, returning plain text."""
        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            
            # Simple html to text helper
            html = r.text
            html = re.sub(r"<(script|style|nav|header|footer|aside|noscript|svg)\b[^>]*>([\s\S]*?)</\1>", "", html, flags=re.IGNORECASE)
            html = re.sub(r"</?(div|p|h[1-6]|li|tr|br\s*/?)\b[^>]*>", "\n", html, flags=re.IGNORECASE)
            html = re.sub(r"<[^>]+>", "", html)
            html = (html.replace('&quot;', '"')
                        .replace('&#x27;', "'")
                        .replace('&amp;', '&')
                        .replace('&gt;', '>')
                        .replace('&lt;', '<')
                        .replace('&nbsp;', ' '))
            lines = [line.strip() for line in html.splitlines()]
            non_empty = [line for line in lines if line]
            text = "\n".join(non_empty)
            
            if len(text) > 8000:
                return "[Content truncated to first 8000 characters]\n\n" + text[:8000]
            return text
        except Exception as e:
            return f"Error fetching webpage: {str(e)}"

    def show_datetime(self) -> str:
        """Returns the current date and time."""
        import datetime
        return f"Current Date and Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    def get_env(self) -> str:
        """Returns sandbox environment info."""
        import platform
        return (
            f"OS: {platform.system()} {platform.release()}\n"
            f"Python Version: {platform.python_version()}\n"
            f"Sandbox Workspace Directory: {SANDBOX_DIR}\n"
        )


# Singleton instance
sandbox = SandboxEnv()
