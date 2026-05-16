from pydantic import BaseModel, field_validator
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.providers.openai import OpenAIProvider

from services.Config.config import AppConfig

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

def build_agent(config: AppConfig) -> Agent:
    """Build a loop-protected agent from AppConfig."""
    api = config.api_config
    model = api.model.strip()
    retry_limit = api.max_loops
    provider_name = api.provider.strip().lower()

    # Route to the correct provider setup
    if provider_name == "ollama":
        model_obj = OpenAIChatModel(
            model,
            provider=OllamaProvider(base_url=api.base_url, api_key=api.api_key),
        )
    elif provider_name in ("openai", "deepseek"):
        # You will likely need a different provider object here (e.g., OpenAIProvider)
        # DeepSeek uses the exact same API structure as OpenAI, so they can usually share this block.
        model_obj = OpenAIChatModel(
            model,
            provider=OpenAIProvider(base_url=api.base_url, api_key=api.api_key),
        )
    else:
        # Fallback to just passing the string if it's an unconfigured provider
        model_obj = model

    return Agent(model_obj, output_type=LoopSafeResponse, retries=retry_limit)

def build_agent_from_json(config_path: str) -> Agent:
    """Load AppConfig from JSON and build the loop-protected agent."""
    return build_agent(config=AppConfig.from_json_file(config_path))


def generate_with_protection(prompt: str, config: AppConfig) -> str:
    print("--- Starting Generation ---")
    try:
        agent = build_agent(config=config)
        # Pydantic AI handles the execution, validation, and retries natively
        result = agent.run_sync(prompt)
        print("\n[Success] Final Output:\n", result.output.conclusion)
        return result.output.conclusion

    except Exception as e:
        # If it still loops after max_retries, Pydantic AI throws a ValidationError
        print(f"\n\n[System Matrix Break]: Loop persisting after max retries. Hard aborting.")
        print(f"Error Details: {e}")
        raise

# Example Usage:
# cfg = AppConfig.from_json_file("./appsettings.json")
# generate_with_protection("Write a story about a time traveler.", config=cfg)
