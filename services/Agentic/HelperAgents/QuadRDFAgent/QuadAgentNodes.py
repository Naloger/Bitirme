import uuid
from typing import cast

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from Config import config
from services.Agentic.HelperAgents.QuadRDFAgent.QuadAgentModels import (
    GraphExtractionResult,
    Quad,
    QuadAgentState,
)
from services.Agentic.HelperAgents.QuadRDFAgent.QuadAgentPrompts import (
    GRAPHRAG_EXTRACTION_PROMPT,
)


def extract_quads_node(state: QuadAgentState) -> QuadAgentState:
    """
    LangGraph node: Prompts the LLM with native structured tool calling
    to extract relationships and parses them into Quads.
    """
    print("[QuadRDFAgent] Running extract_quads_node...")

    text = state.input_text
    if not text:
        return state.model_copy(update={"extracted_quads": [], "error": "No input_text provided"})

    graph_id = state.graph_id or f"graph_{uuid.uuid4().hex[:8]}"
    # Ensure ChatOllama base URL does not conflict by stripping /v1
    base_url = (config.BASE_URL or "http://localhost:11434").removesuffix("/v1")
    llm = ChatOllama(model=config.MODEL, base_url=base_url, temperature=0.0)
    structured_llm = llm.with_structured_output(GraphExtractionResult)

    messages = [
        SystemMessage(content=GRAPHRAG_EXTRACTION_PROMPT),
        HumanMessage(
            content=f"Extract a knowledge graph from the following text:\n\nTEXT:\n{text}"
        ),
    ]

    try:
        extraction = cast(GraphExtractionResult, structured_llm.invoke(messages))

        # Pythonic mapping of relationships directly to Quads
        quads = [
            Quad(
                subject=rel.source,
                predicate=rel.predicate,
                object=rel.target,
                graph=graph_id,
            )
            for rel in extraction.relationships
        ]

        return state.model_copy(update={"extracted_quads": quads, "graph_id": graph_id, "error": None})

    except Exception as e:
        print(f"[QuadRDFAgent] Extraction failed: {e}")
        return state.model_copy(update={"extracted_quads": [], "graph_id": graph_id, "error": str(e)})
