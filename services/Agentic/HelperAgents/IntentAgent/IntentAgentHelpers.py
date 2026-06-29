from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from services.Agentic.HelperAgents.IntentAgent.IntentAgentModels import (
    IntentAgentState,
    IntentResult,
)
from services.Agentic.HelperAgents.IntentAgent.IntentAgentPrompts import SYSTEM_PROMPT
from services.Config import config as cfg
from services.CustomLibs.LLM import get_pydantic_ai_model


def get_agent() -> Agent:
    """Returns the initialized Pydantic-AI Agent configured for Intent analysis."""
    return Agent(
        get_pydantic_ai_model(),
        system_prompt=SYSTEM_PROMPT,
        output_type=IntentResult,
        tool_retries=max(0, int(getattr(cfg, "MAX_LOOPS", 0) or 0)),
        output_retries=max(0, int(getattr(cfg, "MAX_LOOPS", 0) or 0)),
    )

def get_settings() -> ModelSettings:
    """Returns the standard Pydantic-AI ModelSettings payload."""
    return ModelSettings(
        temperature=float(getattr(cfg, "TEMPERATURE", 0.0) or 0.0),
        max_tokens=int(getattr(cfg, "MAX_TOKENS", 2048) or 2048),
        timeout=float(getattr(cfg, "TIMEOUT", 60.0) or 60.0),
    )

def analyze(x: str, k: str = "") -> IntentResult:
    """Invokes the compiled IntentAgent LangGraph to perform parsing."""
    from services.Agentic.HelperAgents.IntentAgent.IntentGraphBuilder import (
        build_intent_graph,
    )

    # IntentAgentState is a Pydantic model
    initial_state = IntentAgentState(
        message_text=x,
        context_info=k,
        analysis_result=None,
        error=None
    )
    
    graph = build_intent_graph()
    result = graph.invoke(initial_state)
    
    if result.get("error"):
        raise ValueError(f"Intent analysis graph failed: {result.get('error')}")
        
    res = result.get("analysis_result")
    assert res is not None
    return res
