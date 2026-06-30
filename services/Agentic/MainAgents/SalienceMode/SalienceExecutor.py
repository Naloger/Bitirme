import json  # Added to format stream chunks securely
import os
import sys
import asyncio
import contextvars
from typing import AsyncIterator

# Ensure project root is in sys.path
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from services.Agentic.MainAgents.SalienceMode.SalienceGraphBuilder import (
    build_salience_graph,
)
from services.Agentic.MainAgents.SalienceMode.SalienceModels import SalienceState

# Context-local variable for stdout redirection callback
stdout_callback_var = contextvars.ContextVar("stdout_callback", default=None)

class ContextLocalStdout:
    def __init__(self, original_stdout):
        self.original_stdout = original_stdout

    def write(self, data):
        self.original_stdout.write(data)
        callback = stdout_callback_var.get()
        if callback:
            try:
                callback(data)
            except Exception:
                pass

    def flush(self):
        self.original_stdout.flush()

    def __getattr__(self, name):
        return getattr(self.original_stdout, name)

# Patch stdout and stderr once
if not isinstance(sys.stdout, ContextLocalStdout):
    sys.stdout = ContextLocalStdout(sys.stdout)
if not isinstance(sys.stderr, ContextLocalStdout):
    sys.stderr = ContextLocalStdout(sys.stderr)

class LineAccumulator:
    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self.buffer = ""
        self.queue = queue
        self.loop = loop

    def add_data(self, data: str):
        self.buffer += data
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line.endswith("\r"):
                line = line[:-1]
            if line.strip():
                # Stream log lines thread-safely
                self.loop.call_soon_threadsafe(
                    self.queue.put_nowait,
                    {"type": "log_line", "line": line}
                )

# 1. Changed to async def and returns an AsyncIterator of strings
async def execute_salience_router_stream(user_input: str) -> AsyncIterator[str]:
    """Streams the LangGraph node updates and stdout logs in real-time as JSON strings."""
    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    accum = LineAccumulator(queue, loop)

    def run_graph_sync():
        token = stdout_callback_var.set(accum.add_data)
        try:
            graph = build_salience_graph()
            initial_state = SalienceState(user_input=user_input)
            state_data = initial_state.model_dump()

            # Emit initial status
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "status", "message": f"Starting graph execution for '{user_input}'"}
            )

            # Iterate the graph execution
            for event in graph.stream(initial_state, stream_mode="updates"):
                for node_name, node_update in event.items():
                    state_data.update(node_update)

                    chunk_payload = {
                        "type": "node_update",
                        "node_name": node_name,
                        "updates": {
                            k: (
                                list(v.keys())
                                if isinstance(v, dict)
                                else len(v)
                                if isinstance(v, list)
                                else str(v)[:200]
                            )
                            for k, v in node_update.items()
                            if v
                        },
                    }
                    loop.call_soon_threadsafe(queue.put_nowait, chunk_payload)

            # Final summary
            final_state = SalienceState(**state_data)
            final_payload = {
                "type": "final_summary",
                "target_subgraph": final_state.target_subgraph,
                "explanation": final_state.explanation,
                "result": final_state.result,
            }
            loop.call_soon_threadsafe(queue.put_nowait, final_payload)

        except Exception as e:
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "error", "message": str(e)}
            )
        finally:
            stdout_callback_var.reset(token)
            # Signal the end of queue stream
            loop.call_soon_threadsafe(queue.put_nowait, None)

    # Start the graph execution in a separate worker thread
    asyncio.create_task(asyncio.to_thread(run_graph_sync))

    # Consume the queue items as they arrive
    while True:
        item = await queue.get()
        if item is None:
            break
        yield json.dumps(item) + "\n"