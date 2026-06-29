import uuid
import instructor
import openai

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
    # Simple keyword routing rule for mock
    if any(k in user_input.lower() for k in ["loop", "transform", "cycle"]):
        return SalienceRouterResponse(
            target="DefaultMode",
            explanation="Mock fallback: Input contains loop/transform keywords, routing to DefaultMode."
        )
    return SalienceRouterResponse(
        target="ExecutiveControlMode",
        explanation="Mock fallback: Defaulting to ExecutiveControlMode for general tasks."
    )


def salience_router_node(state: SalienceState) -> SalienceState:
    """Observes the user input and decides which subgraph to route the task to using structured LLM response."""
    print(f"\n[SalienceRouter] Observing input: '{state.user_input}'...")

    prompt = f"Observe and route this input: '{state.user_input}'"
    messages = [
        {"role": "system", "content": SALIENCE_ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    try:
        response = client.chat.completions.create(
            model=config.MODEL,
            messages=messages,
            response_model=SalienceRouterResponse,
            temperature=0.0,
            timeout=config.TIMEOUT,
        )
    except Exception as e:
        print(f"  [LLM Warning] Connection failed, using mock fallback. Error: {e}")
        response = mock_salience_router(state.user_input)

    target = response.target
    explanation = response.explanation

    print(f"  [Decision] Route to: {target}")
    print(f"  [Explanation] {explanation}")

    return state.model_copy(
        update={
            "target_subgraph": target,
            "explanation": explanation,
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

    loop_graph = build_loop_subgraph()
    loop_init = GraphState(input_text=state.user_input, iteration=0, should_stop=False)
    loop_res = loop_graph.invoke(loop_init)

    # Extract results
    result = ""
    loop_dict = {}
    if hasattr(loop_res, "iteration"):
        actions_count = len(loop_res.decision.get("actions", [])) if hasattr(loop_res, "decision") else 0
        result = f"Completed Loop Subgraph in {loop_res.iteration} iterations. Actions dispatched: {actions_count}"
        loop_dict = loop_res.model_dump()
    elif isinstance(loop_res, dict):
        dec = loop_res.get("decision", {})
        actions_count = len(dec.get("actions", [])) if isinstance(dec, dict) else 0
        result = f"Completed Loop Subgraph in {loop_res.get('iteration', 0)} iterations. Actions dispatched: {actions_count}"
        loop_dict = loop_res

    print(f"  [DefaultMode] Finished. {result}")

    return state.model_copy(
        update={
            "result": result,
            "loop_state": loop_dict,
        }
    )
