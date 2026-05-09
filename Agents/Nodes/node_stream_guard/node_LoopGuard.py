from __future__ import annotations

import logging
from pathlib import Path

from langchain.agents.middleware import (
    AgentState,
)
from typing_extensions import NotRequired

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration Schema
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Custom State Schema for Middleware
# ---------------------------------------------------------------------------
class StreamGuardState(AgentState):
    """Extended agent state for stream guard tracking."""

    stream_guard_output: NotRequired[str]
    stream_guard_thinking: NotRequired[str]
    stream_guard_loop_restarts: NotRequired[int]
    stream_guard_model: NotRequired[str]
    stream_guard_success: NotRequired[bool]


# ---------------------------------------------------------------------------
# Example Usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from Agents.Nodes.node_stream_guard.Functions.create_stream_guard_middleware import (
        create_stream_guard_middleware,
    )

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s"
    )
    base_path = Path(__file__).parent
    input_file = base_path / "Input.txt"
    output_file = base_path / "Output.txt"

    if input_file.exists():
        prompt = input_file.read_text(encoding="utf-8").strip()
        middleware = create_stream_guard_middleware(
            model="qwen3.5:0.8b",
            base_url="http://localhost:11434",
            max_loops=3,
            system_prompt="Be concise and avoid repetitive output.",
        )
        output_text, thinking_text, loop_restarts, success = (
            middleware._execute_stream_with_guard( # type: ignore[attr-defined]
                ollama_messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.7, "num_ctx": 4096},
            )
        )
        report = [
            "provider=ollama",
            f"model={middleware.config.model}",
            f"loop_restarts={loop_restarts}",
            f"success={success}",
            "",
            "[assistant_output]",
            output_text,
            "",
            "[thinking_output]",
            thinking_text,
        ]
        output_file.write_text("\n".join(report).strip() + "\n", encoding="utf-8")
        logger.info("Processed: %s -> %s", input_file, output_file)
    else:
        logger.error("Input file not found: %s", input_file)
