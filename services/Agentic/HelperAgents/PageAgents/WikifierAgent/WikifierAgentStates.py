from typing import Optional, TypedDict

from services.Agentic.HelperAgents.PageAgents.WikifierAgent.WikifierAgentModels import (
    Page,
    WikiPage,
)


class WikifierAgentState(TypedDict):
    """The state payload carrying context and progress through the Wikifier pipeline."""

    page: Page
    current_wiki: Optional[WikiPage]
    error: Optional[str]
