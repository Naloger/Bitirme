import logging

from pydantic import BaseModel, field_validator
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.providers.openai import OpenAIProvider

from services.Config import config

logger = logging.getLogger(__name__)

class LoopSafeResponse(BaseModel):
    conclusion: str

    @field_validator('conclusion')
    @classmethod
    def check_for_loops(cls, value: str) -> str:
        """STAGE 1: The Validation Layer"""
        window_size = 100

        # Ensure we have enough text to check for 3 consecutive windows
        if len(value) >= window_size * 3:
            recent = value[-window_size * 3:]
            chunks = [recent[i:i+window_size] for i in range(0, len(recent), window_size)]

            # If back-to-back duplication is found
            if len(chunks) == 3 and chunks[0] == chunks[1] == chunks[2]:
                looped_phrase = chunks[-1].strip()

                # STAGE 2 & 3: Raising ModelRetry acts as the Interceptor & Feedback Injector
                # Pydantic AI automatically sends this exact string back to the LLM and retries.
                raise ModelRetry(
                    f"! CRITICAL SYSTEM INTERVENTION !\n"
                    f"You got stuck in an infinite thinking loop repeating: '{looped_phrase}'.\n"
                    f"Do NOT repeat that phrase. Do NOT write any more thoughts. "
                    f"Output your final conclusion now."
                )
        return value

def build_agent() -> Agent:
    """Build a loop-protected agent."""
    model_str = config.model.strip()
    retry_limit = config.max_loops
    provider_name = config.provider.strip().lower()

    # Route to the correct provider setup
    if provider_name == "ollama":
        model_obj = OpenAIChatModel(
            model_str,
            provider=OllamaProvider(base_url=config.base_url, api_key=config.api_key),
        )
    elif provider_name in ("openai", "deepseek"):
        model_obj = OpenAIChatModel(
            model_str,
            provider=OpenAIProvider(base_url=config.base_url, api_key=config.api_key),
        )
    else:
        # Fallback to just passing the string if it's an unconfigured provider
        model_obj = model_str

    return Agent(model_obj, output_type=LoopSafeResponse, retries=retry_limit)


def generate_with_protection(prompt: str) -> str:
    logger.info("--- Starting Generation ---")
    try:
        agent = build_agent()
        # Pydantic AI handles the execution, validation, and retries natively
        result = agent.run_sync(prompt)
        logger.info("[Success] Final Output:\n%s", result.output.conclusion)
        return result.output.conclusion

    except (AttributeError, LookupError, OSError, RuntimeError, TypeError, ValueError) as e:
        # If it still loops after max_retries, Pydantic AI throws a ValidationError
        logger.exception("\n\n[System Matrix Break]: Loop persisting after max retries. Hard aborting.")
        logger.error("Error Details: %s", e)
        raise
