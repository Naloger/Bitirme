from typing import cast

from services.Agentic.HelperAgents.IntentAgent.IntentAgentHelpers import (
    get_agent,
    get_settings,
)
from services.Agentic.HelperAgents.IntentAgent.IntentAgentModels import (
    IntentAgentState,
    IntentResult,
)


def analyze_intent_node(state: IntentAgentState) -> IntentAgentState:
    """
    LangGraph node: Analyzes the message text and optional context information,
    producing a structured IntentResult using native structured output.
    """
    print("[IntentAgent] Running analyze_intent_node...")
    
    x = state.message_text
    k = state.context_info or ""
    
    if not x:
        return state.model_copy(update={"error": "No message_text provided"})

    agent = get_agent()
    settings = get_settings()
    
    prompt = f"X: {x}" + (f"\nK: {k}" if k else "")
    
    try:
        response = agent.run_sync(prompt, model_settings=settings)
        partial = cast(IntentResult, response.output)
        
        # Build complete output model matching state signature
        full_result = IntentResult(
            X=x,
            K=k,
            Y=partial.Y,
            Z=partial.Z,
            T=partial.T
        )
        
        return state.model_copy(update={"analysis_result": full_result, "error": None})
    except Exception as e:
        print(f"[IntentAgent] Error in intent analysis: {e}")
        return state.model_copy(update={"error": str(e)})
