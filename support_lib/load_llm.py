import json
import logging
from pathlib import Path
from langchain_ollama import ChatOllama

from llm_config import default_config_candidates, runtime_base_dir

logger = logging.getLogger(__name__)


def load_llm(config_path: Path | None = None) -> ChatOllama:
    """Load ChatOllama from a JSON configuration file.

    If no path is provided, search the runtime directory first (useful for
    frozen EXE builds), then the current working directory.
    """
    if config_path is None:
        config_path = next(
            (
                candidate
                for candidate in default_config_candidates()
                if candidate.exists()
            ),
            runtime_base_dir() / "llm_config.json",
        )

    if not config_path.exists():
        checked = ", ".join(str(p) for p in default_config_candidates())
        raise FileNotFoundError(f"LLM config not found. Checked: {checked}")

    logger.info("Loading LLM config from: %s", config_path)
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    ollama_cfg = cfg["ollama"]

    base_url = ollama_cfg["base_url"]
    model = ollama_cfg["model"]
    temperature = ollama_cfg.get("temperature", 0)
    num_ctx = ollama_cfg.get("num_ctx", 2048)

    logger.info(
        "Initializing ChatOllama: model=%s, base_url=%s, temp=%s, num_ctx=%s",
        model,
        base_url,
        temperature,
        num_ctx,
    )

    return ChatOllama(
        base_url=base_url,
        model=model,
        temperature=temperature,
        num_ctx=num_ctx,
    )
