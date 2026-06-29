import json
import re
import uuid

from services.Agentic.MainAgents.SalienceMode.SalienceModels import SalienceState
from services.Agentic.MainAgents.SalienceMode.SaliencePrompts import (
    SALIENCE_ROUTER_SYSTEM_PROMPT,
)
from services.CustomLibs.LLM.call_llm import call_llm
from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentGraphBuilder import (
    build_loop_subgraph,
)


def salience_router_node(state: SalienceState) -> SalienceState:
    """Observes the user input and decides which subgraph to route the task to."""
    print(f"\n[SalienceRouter] Observing input: '{state.user_input}'...")

    prompt = f"Observe and route this input: '{state.user_input}'"
    response = call_llm(prompt, system_prompt=SALIENCE_ROUTER_SYSTEM_PROMPT)

    target = "ExecutiveControlMode"
    explanation = "Fallback to ExecutiveControlMode due to parsing error."

    try:
        # Extract JSON block robustly
        matches = list(re.finditer(r"\{", response))
        if matches:
            start_idx = matches[-1].start()
            end_idx = response.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx : end_idx + 1]
                data = json.loads(json_str)
                target = data.get("target", "ExecutiveControlMode")
                explanation = data.get("explanation", "")
    except Exception as e:
        print(f"  [SalienceRouter] Error parsing JSON response: {e}")

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
    if hasattr(ecn_res, "reasoning"):
        result = ecn_res.reasoning
        ecn_dict = ecn_res.model_dump()
    elif isinstance(ecn_res, dict):
        result = ecn_res.get("reasoning", "")
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
    loop_init = GraphState(iteration=0, should_stop=False)
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
