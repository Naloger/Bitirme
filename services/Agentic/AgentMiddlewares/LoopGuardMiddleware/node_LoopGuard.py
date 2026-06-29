from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path

from langchain.agents.middleware.tool_selection import logger

from services.Config.config import BASE_URL, MAX_LOOPS, MAX_TOKENS, MODEL, TEMPERATURE

# Ensure project root is in sys.path before importing local services
_root = Path(__file__).resolve().parents[4]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))



# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s"
    )
    base_path = Path(__file__).parent
    input_file = base_path / "Input.txt"
    output_file = base_path / "Output.txt"

    create_stream_guard_middleware = importlib.import_module(
        "services.Agentic.AgentMiddlewares.LoopGuardMiddleware.Functions.create_stream_guard_middleware"
    ).create_stream_guard_middleware

    if input_file.exists():
        prompt = input_file.read_text(encoding="utf-8").strip()
        middleware = create_stream_guard_middleware(
            model=MODEL,
            base_url=BASE_URL,
            max_loops=MAX_LOOPS,
        )
        output_text, thinking_text, loop_restarts, success = (
            middleware._execute_stream_with_guard(
                ollama_messages=[{"role": "user", "content": prompt}],
                options={"temperature": TEMPERATURE, "num_ctx": MAX_TOKENS},
            )
        )
        report = [
            f"provider={getattr(middleware.api_config, 'provider', 'ollama')}",
            f"model={getattr(middleware.api_config, 'model', '')}",
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
