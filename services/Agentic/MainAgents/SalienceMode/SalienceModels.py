from typing import Any, Dict, Optional
from pydantic import BaseModel


class SalienceState(BaseModel):
    """State for the Salience Mode Network router graph."""

    user_input: str
    target_subgraph: str = ""
    explanation: str = ""
    result: str = ""
    ecn_state: Optional[Dict[str, Any]] = None
    loop_state: Optional[Dict[str, Any]] = None
