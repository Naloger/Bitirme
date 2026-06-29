from typing import Optional, cast

from services.Agentic.HelperAgents.PageAgents.WikifierAgent.WikifierAgentModels import (
    Page,
    WikiExtraction,
    WikiPage,
)
from services.Agentic.HelperAgents.PageAgents.WikifierAgent.WikifierAgentPrompts import (
    get_agent,
    get_settings,
)
from services.Agentic.HelperAgents.PageAgents.WikifierAgent.WikifierAgentStates import (
    WikifierAgentState,
)


def _merge(base: Optional[WikiPage], update: WikiExtraction, page: Page) -> WikiPage:
    result = base.model_copy(deep=True) if base else WikiPage(page=page)
    for field in WikiExtraction.model_fields:
        val = getattr(update, field)
        if val:  # skip empty strings, lists, dicts
            setattr(result, field, val)
    return result


def run_pipeline_step(
    state: WikifierAgentState, step_name: str, instruction: str
) -> WikifierAgentState:
    """Executes a single extraction step on the page and merges results into state."""
    print(f"[WikifierAgent] Running step: {step_name}...")
    page = state.get("page")
    if not page or not page.raw_content:
        return {**state, "error": f"No content to parse in step {step_name}"}

    agent = get_agent()
    settings = get_settings()

    try:
        response = agent.run_sync(
            f"Step: {step_name}\n{instruction}\n\nPage text:\n{page.raw_content}",
            model_settings=settings,
        )
        update = cast(WikiExtraction, response.output)

        merged_wiki = _merge(state.get("current_wiki"), update, page)
        return {**state, "current_wiki": merged_wiki, "error": None}
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"[WikifierAgent] Error in step {step_name}: {e}")
        return {**state, "error": str(e)}


# Define explicit node wrappers for each step in the pipeline
def overview_node(state: WikifierAgentState) -> WikifierAgentState:
    return run_pipeline_step(
        state,
        "overview",
        "Extract only the page title and introductory body text. Ignore everything else.",
    )


def sections_node(state: WikifierAgentState) -> WikifierAgentState:
    return run_pipeline_step(
        state,
        "sections",
        "Extract only the section hierarchy (level, heading, content). Ignore everything else.",
    )


def categories_node(state: WikifierAgentState) -> WikifierAgentState:
    return run_pipeline_step(
        state,
        "categories",
        "Extract only categories and disambiguation terms. Ignore everything else.",
    )


def links_node(state: WikifierAgentState) -> WikifierAgentState:
    return run_pipeline_step(
        state,
        "links",
        "Extract only wikilinks, interwiki_links, external_links, and see_also. Ignore everything else.",
    )


def metadata_node(state: WikifierAgentState) -> WikifierAgentState:
    return run_pipeline_step(
        state,
        "metadata",
        "Extract only infobox key-value pairs, references, and templates. Ignore everything else.",
    )
