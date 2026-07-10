from typing import Any

import instructor
import openai

from Config import config
from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentModels import (
    AlignmentAdjustment,
    CollectorInnerResponse,
    CollectorOuterResponse,
    DetectedExternalConflict,
    DetectedInternalInconsistency,
    ExternalCluster,
    FallbackAction,
    FinalExternalAction,
    GraphState,
    InferredLogicalLink,
    IntegratorInnerResponse,
    IntegratorOuterResponse,
    InternalCommunity,
    InternalDirective,
    OrganizerInnerResponse,
    OrganizerOuterResponse,
    Quad,
    ReflectorInnerResponse,
    ReflectorOuterResponse,
    RemediationProposal,
    StateUpdateCommand,
)
from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentPrompts import (
    CollectorNodePromptInner,
    CollectorNodePromptOuter,
    IntegratorNodePromptInner,
    IntegratorNodePromptOuter,
    OrganizerNodePromptInner,
    OrganizerNodePromptOuter,
    ReflectorNodePromptInner,
    ReflectorNodePromptOuter,
)

# Global configuration variable for the active prompt channel
channel = "inner_channel"

# Initialize structured instructor client
client = instructor.from_openai(
    openai.OpenAI(
        base_url=config.BASE_URL if config.BASE_URL else "http://localhost:11434/v1",
        api_key=config.API_KEY if config.API_KEY else "ollama",
    ),
    mode=instructor.Mode.JSON,
)


def call_structured_llm(prompt: str, system_prompt: str, response_model: Any) -> Any:
    """Helper to invoke structured LLM, raising a clear exception if connection fails."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    try:
        return client.chat.completions.create(
            model=config.MODEL,
            messages=messages,
            response_model=response_model,
            temperature=config.TEMPERATURE,
            timeout=config.TIMEOUT,
        )
    except Exception as e:
        print(f"\n[CRITICAL LLM ERROR] Structured LLM call failed in Loop Subgraph: {e}")
        raise RuntimeError(f"Loop Subgraph LLM execution failed: {e}. Fallback is disabled.")


def merge_quads(existing_quads: list[Quad], new_quads: list[Quad]) -> list[Quad]:
    """Helper to deduplicate and merge quads into a list."""
    merged = list(existing_quads)
    seen = {(q.subject, q.predicate, q.object, q.graph) for q in merged}
    for q in new_quads:
        key = (q.subject, q.predicate, q.object, q.graph)
        if key not in seen:
            merged.append(q)
            seen.add(key)
    return merged


# ===========================================================================
# Structured RDF Mock Response Factories (No Scores)
# ===========================================================================

def mock_collector_inner() -> CollectorInnerResponse:
    return CollectorInnerResponse(
        internal_patterns=["Recall pattern identified"],
        internal_anomalies=["Inconsistent statement link"],
        proposed_quads=[
            Quad(subject="worker_node_3", predicate="HAS_METRIC", object="cpu_utilization", graph="knowledge_graph"),
            Quad(subject="cpu_utilization", predicate="HAS_VALUE", object="94.5", graph="knowledge_graph"),
            Quad(subject="worker_node_3", predicate="TRIGGERED", object="WARNING_log", graph="knowledge_graph"),
            Quad(subject="WARNING_log", predicate="HAS_MESSAGE", object="High memory allocation detected on worker_node_3", graph="knowledge_graph")
        ]
    )


def mock_collector_outer() -> CollectorOuterResponse:
    return CollectorOuterResponse(
        external_entities=["api_node", "https://api.example.com/feed"],
        environmental_shifts=["External service down"],
        proposed_quads=[
            Quad(subject="api_node", predicate="STATUS", object="down", graph="llm_input"),
            Quad(subject="api_node", predicate="LOCATED_AT", object="https://api.example.com/feed", graph="llm_input")
        ]
    )


def mock_organizer_inner() -> OrganizerInnerResponse:
    return OrganizerInnerResponse(
        structured_quads=[
            Quad(subject="worker_node_3", predicate="HAS_METRIC", object="cpu_utilization", graph="knowledge_graph"),
            Quad(subject="cpu_utilization", predicate="HAS_VALUE", object="94.5", graph="knowledge_graph"),
            Quad(subject="worker_node_3", predicate="TRIGGERED", object="WARNING_log", graph="knowledge_graph")
        ],
        internal_communities=[InternalCommunity(community_id="sys_resources", member_nodes=["worker_node_3", "cpu_utilization"])],
        logical_corrections_applied=["Removed redundant memory allocation metadata quads"]
    )


def mock_organizer_outer() -> OrganizerOuterResponse:
    return OrganizerOuterResponse(
        structured_quads=[
            Quad(subject="api_node", predicate="STATUS", object="down", graph="llm_input"),
            Quad(subject="api_node", predicate="LOCATED_AT", object="https://api.example.com/feed", graph="llm_input")
        ],
        external_clusters=[ExternalCluster(cluster_id="network_endpoints", member_nodes=["api_node"])],
        inferred_logical_links=[InferredLogicalLink(source="api_node", target="worker_node_3", reasoning="External endpoint down affects processing node")]
    )


def mock_reflector_inner() -> ReflectorInnerResponse:
    return ReflectorInnerResponse(
        detected_internal_inconsistencies=[
            DetectedInternalInconsistency(type="circular", affected_elements=["worker_node_3"], severity="low")
        ],
        remediation_proposals=[
            RemediationProposal(action="pruning", target="WARNING_log", justification="log message cleanup")
        ]
    )


def mock_reflector_outer() -> ReflectorOuterResponse:
    return ReflectorOuterResponse(
        detected_external_conflicts=[
            DetectedExternalConflict(type="noise", affected_elements=["api_node"], context_clash="outdated")
        ],
        alignment_adjustments=[
            AlignmentAdjustment(action="reweight", target="api_node", justification="stale status checks")
        ]
    )


def mock_integrator_inner() -> IntegratorInnerResponse:
    return IntegratorInnerResponse(
        internal_directives=[
            InternalDirective(priority=1, action="prune_edge", target_component="warning_subgraph", parameters={})
        ],
        state_update_commands=[
            StateUpdateCommand(command="prune", payload={})
        ],
        requires_re_evaluation=False,
        decision_rationale="Entity conflict resolved, pruning redundant warning nodes."
    )


def mock_integrator_outer() -> IntegratorOuterResponse:
    return IntegratorOuterResponse(
        final_external_action=FinalExternalAction(action_name="dispatch_alert", mcp_tool_name="graph_sync_tool", parameters={}, execution_priority=1),
        expected_external_outcome="Successful authentication",
        fallback_action=FallbackAction(action_name="trigger_fallback", parameters={}),
        final_decision_rationale="Dispatching graph synchronization request for down node."
    )


# ===========================================================================
# Graph Node Implementations (RDF Quadstore Architecture - No Scores)
# ===========================================================================

def collector_node(state: GraphState) -> GraphState:
    channel = state.channel
    # Safeguard: if we are in inner_channel but have user input_text, escalate to outer_channel to parse/build the graph
    if channel == "inner_channel" and state.input_text:
        print(f"  [Safeguard] Active user input detected in inner_channel. Auto-escalating channel to outer_channel to build knowledge graph.")
        channel = "outer_channel"

    print(f"\n[collector_node] Executing channel: {channel}...")
    llm_outputs = dict(state.llm_outputs)
    raw_internal = list(state.raw_internal)
    raw_external = list(state.raw_external)
    knowledge_graph = list(state.knowledge_graph)

    if channel == "inner_channel":
        # Connect to collector tools as a trigger / progress indicator
        from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentTools import (
            tool_ingest_internal_stream,
            tool_write_to_quadstore,
        )
        ingested = tool_ingest_internal_stream(source="llm_input")
        # Load the ingested quads from the database into the state's knowledge_graph
        ingested_quads = [Quad(**q) for q in ingested]
        knowledge_graph = merge_quads(knowledge_graph, ingested_quads)

        system_prompt = CollectorNodePromptInner.format(current_internal_state=knowledge_graph)
        prompt = "Analyze inner knowledge graph quads to identify latent patterns."
        response = call_structured_llm(prompt, system_prompt, CollectorInnerResponse)
        if not response.proposed_quads:
            print("  [LLM Warning] Empty proposed_quads returned from inner collector. Continuing with empty set.")
        llm_outputs["collector"] = response.model_dump()
        raw_internal.append({"source": "internal", "data": "collector_ingested"})
        
        # Merge directly to the shared store
        proposed = [Quad(**q) for q in response.model_dump().get("proposed_quads", [])]
        knowledge_graph = merge_quads(knowledge_graph, proposed)
    elif channel == "outer_channel":
        # Connect to collector tools as a trigger / progress indicator
        from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentTools import (
            tool_ingest_external_api,
            tool_write_to_quadstore,
        )
        ingested = tool_ingest_external_api()
        tool_write_to_quadstore(ingested)

        intent_str = ""
        if state.intent_result:
            intent_str = (
                f"\nIntent Analysis Context:\n"
                f"- Sender Identity: {state.intent_result.sender_identity}\n"
                f"- Inferences: {state.intent_result.inferences}\n"
                f"- Recommended Action: {state.intent_result.recommended_action}"
            )
        system_prompt = CollectorNodePromptOuter.format(
            input_text=state.input_text,
            intent_context=intent_str
        )
        prompt = "Extract atomic facts from standard input text."
        response = call_structured_llm(prompt, system_prompt, CollectorOuterResponse)
        if not response.proposed_quads:
            print("  [LLM Warning] Empty proposed_quads returned from outer collector. Continuing with empty set.")
        llm_outputs["collector"] = response.model_dump()
        raw_external.append({"source": "external", "data": "collector_ingested"})

        # Merge directly to the shared store
        proposed = [Quad(**q) for q in response.model_dump().get("proposed_quads", [])]
        knowledge_graph = merge_quads(knowledge_graph, proposed)

    return state.model_copy(update={
        "llm_outputs": llm_outputs,
        "raw_internal": raw_internal,
        "raw_external": raw_external,
        "knowledge_graph": knowledge_graph,
        "channel": channel
    })


def organizer_node(state: GraphState) -> GraphState:
    channel = state.channel
    print(f"\n[organizer_node] Executing channel: {channel}...")
    llm_outputs = dict(state.llm_outputs)
    knowledge_graph = list(state.knowledge_graph)

    # Connect to organizer tools as a trigger / progress indicator on the shared store
    from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentTools import (
        tool_index_quads,
        tool_map_ontology,
        tool_run_community_detection,
    )
    tool_run_community_detection(knowledge_graph)
    tool_map_ontology(knowledge_graph)
    tool_index_quads(knowledge_graph)

    if channel == "inner_channel":
        system_prompt = OrganizerNodePromptInner.format(proposed_quads=knowledge_graph)
        prompt = "Apply ontology constraints and logical standardization to knowledge graph."
        response = call_structured_llm(prompt, system_prompt, OrganizerInnerResponse)
        if not response.structured_quads:
            print("  [LLM Warning] Empty structured_quads returned from inner organizer. Continuing with empty set.")
        llm_outputs["organizer"] = response.model_dump()
        
        # Replace graph with organized structured quads
        structured = [Quad(**q) for q in response.model_dump().get("structured_quads", [])]
        knowledge_graph = structured
    elif channel == "outer_channel":
        system_prompt = OrganizerNodePromptOuter.format(proposed_quads=knowledge_graph)
        prompt = "Apply logical hierarchy and mapping rules to knowledge graph."
        response = call_structured_llm(prompt, system_prompt, OrganizerOuterResponse)
        if not response.structured_quads:
            print("  [LLM Warning] Empty structured_quads returned from outer organizer. Continuing with empty set.")
        llm_outputs["organizer"] = response.model_dump()

        # Replace graph with organized structured quads
        structured = [Quad(**q) for q in response.model_dump().get("structured_quads", [])]
        knowledge_graph = structured

    return state.model_copy(update={
        "llm_outputs": llm_outputs,
        "knowledge_graph": knowledge_graph
    })


def reflector_node(state: GraphState) -> GraphState:
    channel = state.channel
    print(f"\n[reflector_node] Executing channel: {channel}...")
    llm_outputs = dict(state.llm_outputs)
    validation_report = dict(state.validation_report)
    knowledge_graph = list(state.knowledge_graph)

    # Connect to reflector tools as a trigger / progress indicator on the shared store
    from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentTools import (
        tool_detect_anomalies,
        tool_infer_missing_quads,
        tool_validate_quads,
    )
    issues = tool_validate_quads(knowledge_graph)
    tool_detect_anomalies(knowledge_graph)
    tool_infer_missing_quads(knowledge_graph, issues)

    if channel == "inner_channel":
        system_prompt = ReflectorNodePromptInner.format(structured_quads=knowledge_graph)
        prompt = "Check internal consistency and record remediation proposals."
        response = call_structured_llm(prompt, system_prompt, ReflectorInnerResponse)
        llm_outputs["reflector"] = response.model_dump()

        validation_report["issues"] = response.model_dump().get("detected_internal_inconsistencies", [])
        validation_report["proposals"] = response.model_dump().get("remediation_proposals", [])
    elif channel == "outer_channel":
        system_prompt = ReflectorNodePromptOuter.format(structured_quads=knowledge_graph)
        prompt = "Cross-reference external quads with standard LLM input text."
        response = call_structured_llm(prompt, system_prompt, ReflectorOuterResponse)
        llm_outputs["reflector"] = response.model_dump()

        validation_report["issues"] = response.model_dump().get("detected_external_conflicts", [])
        validation_report["proposals"] = response.model_dump().get("alignment_adjustments", [])

    return state.model_copy(update={
        "llm_outputs": llm_outputs,
        "validation_report": validation_report
    })


def integrator_node(state: GraphState) -> GraphState:
    channel = state.channel
    print(f"\n[integrator_node] Executing channel: {channel}...")
    llm_outputs = dict(state.llm_outputs)
    decision = dict(state.decision)
    iteration = state.iteration + 1
    should_stop = state.should_stop
    knowledge_graph = list(state.knowledge_graph)
    proposals = state.validation_report.get("proposals", [])

    if channel == "inner_channel":
        system_prompt = IntegratorNodePromptInner.format(knowledge_graph=knowledge_graph, remediation_proposals=proposals)
        prompt = "Merge proposals with knowledge graph and prioritizedirectives."
        response = call_structured_llm(prompt, system_prompt, IntegratorInnerResponse)
        llm_outputs["integrator"] = response.model_dump()

        decision["actions"] = [
            {
                "type": d.get("action", "directive"),
                "target": d.get("target_component", "system"),
                "concept": d.get("action", "directive")
            }
            for d in response.model_dump().get("internal_directives", [])
        ]
    elif channel == "outer_channel":
        system_prompt = IntegratorNodePromptOuter.format(knowledge_graph=knowledge_graph, internal_directives=llm_outputs.get('integrator', {}))
        prompt = "Merge external context with knowledge graph and translate to actions."
        response = call_structured_llm(prompt, system_prompt, IntegratorOuterResponse)
        llm_outputs["integrator"] = response.model_dump()

        action = response.final_external_action
        if action:
            decision["actions"] = [
                {
                    "type": action.action_name,
                    "target": action.mcp_tool_name,
                    "concept": action.action_name
                }
            ]
        else:
            decision["actions"] = []

    # Connect to integrator tools as a trigger / progress indicator on the shared store
    from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentTools import (
        tool_dispatch_action,
        tool_quadstore_impact_analysis,
        tool_quadstore_traversal,
    )
    
    priority_nodes = tool_quadstore_traversal(knowledge_graph)
    tool_quadstore_impact_analysis(priority_nodes, knowledge_graph)
    for action in decision["actions"]:
        tool_dispatch_action(action)

    if iteration >= 3:
        should_stop = True
    return state.model_copy(update={
        "llm_outputs": llm_outputs,
        "decision": decision,
        "iteration": iteration,
        "should_stop": should_stop
    })


def _loop_or_exit(state: GraphState) -> str:
    """
    Called after Node4.
    Returns 'loop' to go back to Node1, or 'exit' to END.
    """
    return "exit" if state.should_stop else "loop"
