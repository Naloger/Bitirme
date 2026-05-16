from __future__ import annotations

from typing import Optional

from services.AgentMiddlewares.LoopGuardMiddleware.Classes.StreamGuardMiddleware import (
    StreamGuardMiddleware,
)
from services.Config.config import AppConfig, APILLMConfig


def create_stream_guard_middleware(
    app_config: Optional[AppConfig] = None,
    config_file: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    max_loops: Optional[int] = None,
) -> StreamGuardMiddleware:
    """Create StreamGuardMiddleware using config.py models with optional overrides."""
    if app_config is not None:
        resolved_config = app_config.model_copy(deep=True)
    elif config_file:
        resolved_config = AppConfig.from_json_file(config_file)
    else:
        resolved_config = AppConfig()

    config_params = {}
    if model is not None:
        config_params["model"] = model
    if base_url is not None:
        config_params["base_url"] = base_url
    if max_loops is not None:
        config_params["max_loops"] = max_loops

    if config_params:
        resolved_api = resolved_config.api_config.model_copy(update=config_params)
        resolved_config = resolved_config.model_copy(
            update={"api_config": APILLMConfig.model_validate(resolved_api.model_dump())}
        )

    return StreamGuardMiddleware(config=resolved_config)

