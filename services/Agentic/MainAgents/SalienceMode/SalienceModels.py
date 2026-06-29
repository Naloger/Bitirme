from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class SalienceRouterResponse(BaseModel):
    """Structured response for Salience Router."""
    target: str = Field(description="The target subgraph to route to, strictly one of: 'DefaultMode' or 'ExecutiveControlMode'.")
    explanation: str = Field(description="A clear, logical reasoning explaining the routing decision.")


class SalienceState(BaseModel):
    """State for the Salience Mode Network router graph."""

    user_input: str
    target_subgraph: str = ""
    explanation: str = ""
    result: str = ""
    ecn_state: Optional[Dict[str, Any]] = None
    loop_state: Optional[Dict[str, Any]] = None
