from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class StreamGuardConfig(BaseModel):
    """Configuration for StreamGuardMiddleware."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    # Ollama connection
    base_url: str = "http://localhost:11434"
    model: str = "qwen3.5:0.8b"
    timeout_seconds: int = 60

    # Generation parameters
    temperature: float = 0.7
    num_ctx: int = 4096
    top_p: Optional[float] = 0.9
    repeat_penalty: Optional[float] = 1.1

    # Loop guard parameters
    max_loops: int = 2
    max_repeated_chunk: int = 4
    repetition_window: int = 16
    pre_content_chunk_limit: int = 300

    # System prompt
    system_prompt: Optional[str] = None
