from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.Agentic.HelperAgents.IntentAgent.IntentAgentModels import IntentResult



# ===========================================================================
# Core RDF Quad model
# ===========================================================================

class Quad(BaseModel):
    subject: str = Field(description="The source entity/node in the RDF quad.")
    predicate: str = Field(description="The predicate/relationship connecting subject to object (in uppercase, e.g., HAS_METRIC, STATUS, OCCURRED).")
    object: str = Field(description="The target entity, concept, or literal value in the RDF quad.")
    graph: str = Field(description="The named graph or context identifier (e.g., 'knowledge_graph', 'llm_input').")


# ===========================================================================
# 1. Collector Structured Outputs
# ===========================================================================

class CollectorInnerResponse(BaseModel):
    internal_patterns: List[str] = Field(default_factory=list)
    internal_anomalies: List[str] = Field(default_factory=list)
    proposed_quads: List[Quad] = Field(
        default_factory=list,
        description="RDF quads recalled from the existing knowledge graph."
    )


class CollectorOuterResponse(BaseModel):
    external_entities: List[str] = Field(default_factory=list)
    environmental_shifts: List[str] = Field(default_factory=list)
    proposed_quads: List[Quad] = Field(
        default_factory=list,
        description="Factual RDF quads parsed from the standard LLM input text."
    )


# ===========================================================================
# 2. Organizer Structured Outputs
# ===========================================================================

class InternalCommunity(BaseModel):
    community_id: str
    member_nodes: List[str] = Field(default_factory=list)


class OrganizerInnerResponse(BaseModel):
    structured_quads: List[Quad] = Field(default_factory=list)
    internal_communities: List[InternalCommunity] = Field(default_factory=list)
    logical_corrections_applied: List[str] = Field(default_factory=list)


class ExternalCluster(BaseModel):
    cluster_id: str
    member_nodes: List[str] = Field(default_factory=list)


class InferredLogicalLink(BaseModel):
    source: str
    target: str
    reasoning: str


class OrganizerOuterResponse(BaseModel):
    structured_quads: List[Quad] = Field(default_factory=list)
    external_clusters: List[ExternalCluster] = Field(default_factory=list)
    inferred_logical_links: List[InferredLogicalLink] = Field(default_factory=list)


# ===========================================================================
# 3. Reflector Structured Outputs
# ===========================================================================

class DetectedInternalInconsistency(BaseModel):
    type: str
    affected_elements: List[str] = Field(default_factory=list)
    severity: str


class RemediationProposal(BaseModel):
    action: str
    target: str
    justification: str


class ReflectorInnerResponse(BaseModel):
    detected_internal_inconsistencies: List[DetectedInternalInconsistency] = Field(
        default_factory=list
    )
    remediation_proposals: List[RemediationProposal] = Field(default_factory=list)


class DetectedExternalConflict(BaseModel):
    type: str
    affected_elements: List[str] = Field(default_factory=list)
    context_clash: str


class AlignmentAdjustment(BaseModel):
    action: str
    target: str
    justification: str


class ReflectorOuterResponse(BaseModel):
    detected_external_conflicts: List[DetectedExternalConflict] = Field(
        default_factory=list
    )
    alignment_adjustments: List[AlignmentAdjustment] = Field(default_factory=list)


# ===========================================================================
# 4. Integrator Structured Outputs
# ===========================================================================

class InternalDirective(BaseModel):
    priority: int
    action: str
    target_component: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class StateUpdateCommand(BaseModel):
    command: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class IntegratorInnerResponse(BaseModel):
    internal_directives: List[InternalDirective] = Field(default_factory=list)
    state_update_commands: List[StateUpdateCommand] = Field(default_factory=list)
    requires_re_evaluation: bool
    decision_rationale: str


class FinalExternalAction(BaseModel):
    action_name: str
    mcp_tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    execution_priority: int


class FallbackAction(BaseModel):
    action_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class IntegratorOuterResponse(BaseModel):
    final_external_action: Optional[FinalExternalAction] = None
    expected_external_outcome: str
    fallback_action: Optional[FallbackAction] = None
    final_decision_rationale: str



# ===========================================================================
# Main Graph State
# ===========================================================================

class GraphState(BaseModel):
    """Central state object passed between every node."""

    raw_internal: List[Dict[str, Any]] = Field(default_factory=list)
    raw_external: List[Dict[str, Any]] = Field(default_factory=list)
    should_stop: bool = False
    iteration: int = 0
    llm_outputs: Dict[str, Any] = Field(default_factory=dict)
    knowledge_graph: List[Quad] = Field(default_factory=list)
    validation_report: Dict[str, Any] = Field(default_factory=dict)
    decision: Dict[str, Any] = Field(default_factory=dict)
    input_text: str = ""
    channel: str = "inner_channel"
    intent_result: Optional[IntentResult] = None
