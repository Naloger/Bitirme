import uuid
import instructor
import openai
import json
import traceback

from Config import config
from services.Agentic.MainAgents.SalienceMode.SalienceModels import (
    SalienceRouterResponse,
    SalienceState,
)
from services.Agentic.MainAgents.SalienceMode.SaliencePrompts import (
    SALIENCE_ROUTER_SYSTEM_PROMPT,
)
from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentGraphBuilder import (
    build_loop_subgraph,
)

# Initialize structured instructor client
client = instructor.from_openai(
    openai.OpenAI(
        base_url=config.BASE_URL if config.BASE_URL else "http://localhost:11434/v1",
        api_key=config.API_KEY if config.API_KEY else "ollama",
    ),
    mode=instructor.Mode.JSON,
)


def mock_salience_router(user_input: str) -> SalienceRouterResponse:
    """Mock fallback for salience router when LLM call fails."""
    channel = "inner_channel"
    if any(k in user_input.lower() for k in ["outer", "external"]):
        channel = "outer_channel"
    # Simple keyword routing rule for mock
    if any(k in user_input.lower() for k in ["loop", "transform", "cycle"]):
        return SalienceRouterResponse(
            target="DefaultMode",
            explanation="Mock fallback: Input contains loop/transform keywords, routing to DefaultMode.",
            channel=channel
        )
    return SalienceRouterResponse(
        target="ExecutiveControlMode",
        explanation="Mock fallback: Defaulting to ExecutiveControlMode for general tasks.",
        channel=channel
    )

def run_intent_analysis_node(state: SalienceState) -> SalienceState:
    """Invokes the IntentAgent helper to analyze user intent before routing."""
    print("\n==================================================")
    print("[IntentAnalysisNode] RUNNING INTENT ANALYSIS...")
    print(f"  Input Message: '{state.user_input}'")
    print("==================================================")
    from services.Agentic.HelperAgents.IntentAgent.IntentAgentHelpers import analyze
    try:
        intent_res = analyze(message_text=state.user_input, context_info="")
        print("[IntentAnalysisNode] ANALYSIS COMPLETED SUCCESSFULLY:")
        print(f"  • Sender Identity:      {intent_res.sender_identity}")
        print(f"  • Situation Inferences:  {intent_res.inferences}")
        print(f"  • Recommended Action:   {intent_res.recommended_action}")
        print("==================================================\n")
        return state.model_copy(update={"intent_result": intent_res})
    except Exception as e:
        print(f"  [IntentAgent Warning] Intent analysis failed: {e}")
        print("==================================================\n")
        return state


def salience_router_node(state: SalienceState) -> SalienceState:
    """Observes the user input and decides which subgraph to route the task to using structured LLM response."""
    print(f"\n[SalienceRouter] Observing input: '{state.user_input}'...")

    prompt = f"Observe and route this input: '{state.user_input}'"
    if state.intent_result:
        print("\n==================================================")
        print("[SalienceRouter] PASSING INTENT CONTEXT TO LLM:")
        print(f"  • Sender Identity:      {state.intent_result.sender_identity}")
        print(f"  • Situation Inferences:  {state.intent_result.inferences}")
        print(f"  • Recommended Action:   {state.intent_result.recommended_action}")
        print("==================================================\n")
        prompt += (
            f"\n\nIntent Analysis Context:\n"
            f"- Sender Identity: {state.intent_result.sender_identity}\n"
            f"- Inferences/Speculations: {state.intent_result.inferences}\n"
            f"- Recommended Action: {state.intent_result.recommended_action}\n"
        )

    messages = [
        {"role": "system", "content": SALIENCE_ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    print("\n[LLM Execution] Calling Salience Router LLM:")
    print(f"  Model: {config.MODEL}")
    print(f"  Temperature: 0.0")
    print(f"  Timeout: {config.TIMEOUT}")
    print(f"  Messages: {json.dumps(messages, indent=2)}")

    try:
        response = client.chat.completions.create(
            model=config.MODEL,
            messages=messages,
            response_model=SalienceRouterResponse,
            temperature=0.0,
            timeout=config.TIMEOUT,
        )
        print("[LLM Response] Success!")
        if hasattr(response, "model_dump_json"):
            print(f"  Response: {response.model_dump_json(indent=2)}")
        elif hasattr(response, "model_dump"):
            print(f"  Response: {json.dumps(response.model_dump(), indent=2)}")
        else:
            print(f"  Response: {response}")
    except Exception as e:
        print(f"  [LLM Warning] Connection failed, using mock fallback. Error: {e}")
        traceback.print_exc()
        response = mock_salience_router(state.user_input)

    target = response.target
    explanation = response.explanation
    channel = response.channel

    # Safeguard: if user input is present, it is an external prompt and needs to be parsed, so it MUST use outer_channel
    if state.user_input and channel == "inner_channel":
        print(f"  [Safeguard] User input detected. Auto-escalating channel to outer_channel to ensure message parsing.")
        channel = "outer_channel"

    print(f"  [Decision] Route to: {target}")
    print(f"  [Explanation] {explanation}")
    print(f"  [Channel] Channel: {channel}")

    return state.model_copy(
        update={
            "target_subgraph": target,
            "explanation": explanation,
            "channel": channel,
        }
    )


def run_executive_subgraph(state: SalienceState) -> SalienceState:
    """Wraps and executes the Executive Control Network (ECN) subgraph."""
    print("\n[SalienceRouter] Executing ExecutiveControlMode subgraph...")
    from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlExecutor import (
        default_initial_state,
    )
    from services.Agentic.MainAgents.ExecutiveControlMode.ExecutiveControlGraphBuilder import (
        build_ecn_graph,
    )

    ecn_graph = build_ecn_graph()
    task_id = f"salience_{uuid.uuid4().hex[:8]}"

    ecn_init = default_initial_state(task_id=task_id, task=state.user_input)
    ecn_res = ecn_graph.invoke(ecn_init)

    # Extract results
    result = ""
    ecn_dict = {}
    if hasattr(ecn_res, "final_answer"):
        result = ecn_res.final_answer or ecn_res.reasoning
        ecn_dict = ecn_res.model_dump()
    elif isinstance(ecn_res, dict):
        result = ecn_res.get("final_answer", "") or ecn_res.get("reasoning", "")
        ecn_dict = ecn_res

    print(f"  [ExecutiveControlMode] Finished. Output length: {len(result)}")

    return state.model_copy(
        update={
            "result": result,
            "ecn_state": ecn_dict,
        }
    )


def run_default_subgraph(state: SalienceState) -> SalienceState:
    """Wraps and executes the Default Mode (Loop) subgraph."""
    print("\n[SalienceRouter] Executing DefaultMode subgraph...")
    from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentModels import (
        GraphState,
    )
    from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentTools import (
        tool_write_to_quadstore,
    )

    loop_graph = build_loop_subgraph()
    loop_init = GraphState(
        input_text=state.user_input,
        iteration=0,
        should_stop=False,
        channel=state.channel,
        intent_result=state.intent_result,
    )
    loop_res = loop_graph.invoke(loop_init)

    # Extract results
    result = ""
    loop_dict = {}
    final_quads = []
    if hasattr(loop_res, "iteration"):
        actions_count = len(loop_res.decision.get("actions", [])) if hasattr(loop_res, "decision") else 0
        result = f"Completed Loop Subgraph in {loop_res.iteration} iterations. Actions dispatched: {actions_count}"
        loop_dict = loop_res.model_dump()
        final_quads = list(loop_res.knowledge_graph) if hasattr(loop_res, "knowledge_graph") else []
    elif isinstance(loop_res, dict):
        dec = loop_res.get("decision", {})
        actions_count = len(dec.get("actions", [])) if isinstance(dec, dict) else 0
        result = f"Completed Loop Subgraph in {loop_res.get('iteration', 0)} iterations. Actions dispatched: {actions_count}"
        loop_dict = loop_res
        final_quads = loop_res.get("knowledge_graph", [])

    # Persist final compiled quads to Apache AGE graph database
    if final_quads:
        print(f"  [DefaultMode] Persisting {len(final_quads)} compiled quads to Apache AGE quadstore...")
        try:
            tool_write_to_quadstore(final_quads, overwrite=True, clear_contexts=["llm_input"])
            print(f"  [DefaultMode] Successfully wrote {len(final_quads)} quads to Apache AGE.")
        except Exception as e:
            print(f"  [DefaultMode WARNING] Failed to persist quads to Apache AGE: {e}")
    else:
        print("  [DefaultMode] No quads to persist (knowledge graph is empty).")

    print(f"  [DefaultMode] Finished. {result}")

    return state.model_copy(
        update={
            "result": result,
            "loop_state": loop_dict,
        }
    )
