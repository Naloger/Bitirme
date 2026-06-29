from functools import lru_cache
from typing import Any

from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.providers.openai import OpenAIProvider

from Config import config


@lru_cache(maxsize=1)
def get_pydantic_ai_model() -> Any:
    """
    Returns the configured Pydantic-AI model instance based on settings.
    """
    provider = str(getattr(config, "PROVIDER", "ollama") or "ollama").lower()
    name = str(getattr(config, "MODEL", "llama3.1") or "llama3.1")
    url = str(
        getattr(config, "BASE_URL", "http://localhost:11434") or "http://localhost:11434"
    )
    key = getattr(config, "API_KEY", None)
    if provider == "ollama":
        return OllamaModel(name, provider=OllamaProvider(base_url=url, api_key=key))
    if provider in ("openai", "deepseek"):
        return OpenAIChatModel(name, provider=OpenAIProvider(base_url=url, api_key=key))
    return name
