from __future__ import annotations
from pathlib import Path
import sys
import logging
import importlib
from langchain.agents.middleware.tool_selection import logger
from services.Config.config import AppConfig
# Ensure the repository root (outer 'services' folder) is on sys.path so
# package-style imports (e.g. 'services.Config.config') work when this file is
# executed directly as a script.


_root = Path(__file__).resolve().parents[3]
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

    # Try to load AppConfig from the project's Config/config.json if present
    project_root = Path(__file__).resolve().parents[2]
    config_file = project_root / "Config" / "config.json"

    config = (
        AppConfig.from_json_file(str(config_file))
        if config_file.exists()
        else AppConfig()
    )
    api = config.api_config
    create_stream_guard_middleware = importlib.import_module(
        "services.AgentMiddlewares.LoopGuardMiddleware.Functions.create_stream_guard_middleware"
    ).create_stream_guard_middleware

    if input_file.exists():
        prompt = input_file.read_text(encoding="utf-8").strip()
        middleware = create_stream_guard_middleware(
            model=api.model,
            base_url=api.base_url,
            max_loops=api.max_loops,
        )
        output_text, thinking_text, loop_restarts, success = (
            middleware._execute_stream_with_guard(
                ollama_messages=[{"role": "user", "content": prompt}],
                options={"temperature": api.temperature, "num_ctx": api.max_tokens},
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
