"""
Generalized Pydantic-AI helpers used across all LangGraph agents.

Centralizes the shared `get_agent` and `get_settings` factory functions
so individual agent helpers no longer need to duplicate them.
"""

from typing import Type

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from services.Config import config as cfg
from services.CustomLibs.LLM import get_pydantic_ai_model


def get_agent(
    system_prompt: str,
    output_type: Type[BaseModel],
    *,
    tool_retries: int | None = None,
    output_retries: int | None = None,
) -> Agent:
    """
    Returns a Pydantic-AI Agent configured with the global LLM settings.

    Args:
        system_prompt: The system prompt for the agent.
        output_type: The Pydantic model class the agent should return.
        tool_retries: Override for tool retry count (defaults to config.MAX_LOOPS).
        output_retries: Override for output retry count (defaults to config.MAX_LOOPS).
    """
    retries = max(0, int(getattr(cfg, "MAX_LOOPS", 0) or 0))
    return Agent(
        get_pydantic_ai_model(),
        system_prompt=system_prompt,
        output_type=output_type,
        tool_retries=tool_retries if tool_retries is not None else retries,
        output_retries=output_retries if output_retries is not None else retries,
    )


def get_settings(
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
) -> ModelSettings:
    """
    Returns a Pydantic-AI ModelSettings payload from global config.

    All parameters are optional overrides; when omitted the value
    is read from the project-wide config module.
    """
    return ModelSettings(
        temperature=temperature if temperature is not None else float(getattr(cfg, "TEMPERATURE", 0.0) or 0.0),
        max_tokens=max_tokens if max_tokens is not None else int(getattr(cfg, "MAX_TOKENS", 2048) or 2048),
        timeout=timeout if timeout is not None else float(getattr(cfg, "TIMEOUT", 60.0) or 60.0),
    )
