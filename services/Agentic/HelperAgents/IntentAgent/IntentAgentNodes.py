from typing import cast

from services.Agentic.HelperAgents.IntentAgent.IntentAgentModels import (
    IntentAgentState,
    IntentResult,
    IntentAnalysisOutput,
)
from services.Agentic.HelperAgents.IntentAgent.IntentAgentPrompts import SYSTEM_PROMPT
from services.CustomLibs.LLM.pydantic_ai_helpers import get_agent, get_settings


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

    agent = get_agent(system_prompt=SYSTEM_PROMPT, output_type=IntentAnalysisOutput)
    settings = get_settings()
    
    prompt = f"Ham Mesaj (message_text): {x}" + (f"\nBağlam Bilgisi (context_info): {k}" if k else "")
    
    try:
        response = agent.run_sync(prompt, model_settings=settings)
        partial = cast(IntentAnalysisOutput, response.output)
        
        # Build complete output model matching state signature
        full_result = IntentResult(
            message_text=x,
            context_info=k,
            sender_identity=partial.sender_identity,
            inferences=partial.inferences,
            recommended_action=partial.recommended_action
        )
        
        return state.model_copy(update={"analysis_result": full_result, "error": None})
    except Exception as e:
        print(f"[IntentAgent] Error in intent analysis: {e}")
        return state.model_copy(update={"error": str(e)})
