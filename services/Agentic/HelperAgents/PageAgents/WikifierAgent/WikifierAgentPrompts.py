from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from services.Agentic.HelperAgents.PageAgents.WikifierAgent.WikifierAgentModels import (
    WikiExtraction,
)
from services.Config import config as cfg

# Pipeline definition
STEPS = [
    (
        "overview",
        "Extract only the page title and introductory body text. Ignore everything else.",
    ),
    (
        "sections",
        "Extract only the section hierarchy (level, heading, content). Ignore everything else.",
    ),
    (
        "categories",
        "Extract only categories and disambiguation terms. Ignore everything else.",
    ),
    (
        "links",
        "Extract only wikilinks, interwiki_links, external_links, and see_also. Ignore everything else.",
    ),
    (
        "metadata",
        "Extract only infobox key-value pairs, references, and templates. Ignore everything else.",
    ),
]

SYSTEM_PROMPT = (
    "You are an expert Wikipedia editor. Return only structured data matching the schema.\n"
    "CRITICAL: The output MUST be a JSON object matching the WikiExtraction schema. "
    "DO NOT return a JSON array/list directly under any circumstances. "
    "If extracting sections, categories, see_also, external_links, or references, wrap them "
    "under their corresponding keys inside the root JSON object."
)


from services.CustomLibs.LLM import get_pydantic_ai_model


def get_agent() -> Agent:
    return Agent(
        get_pydantic_ai_model(),
        system_prompt=SYSTEM_PROMPT,
        output_type=WikiExtraction,
        tool_retries=max(0, int(getattr(cfg, "MAX_LOOPS", 0) or 0)),
        output_retries=max(0, int(getattr(cfg, "MAX_LOOPS", 0) or 0)),
    )


def get_settings() -> ModelSettings:
    return ModelSettings(
        temperature=float(getattr(cfg, "TEMPERATURE", 0.0) or 0.0),
        max_tokens=int(getattr(cfg, "MAX_TOKENS", 2048) or 2048),
        timeout=float(getattr(cfg, "TIMEOUT", 60.0) or 60.0),
    )
