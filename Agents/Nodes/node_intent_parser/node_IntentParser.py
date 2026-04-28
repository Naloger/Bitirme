from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field

from support_lib.load_llm import load_llm

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
INPUT_FILE = BASE / "Input.txt"
OUTPUT_FILE = BASE / "Output.txt"


@lru_cache(maxsize=1)
def get_llm():
    """Load and cache the shared LLM client on first use."""
    return load_llm()



# ── 2. Type-Safe State Definition ────────────────────────────────────────────
# This custom TypedDict replaces MessagesState to appease strict type checkers
class AgentState(BaseModel):
    messages: Annotated[list[BaseMessage], add_messages]


# ── 3. Tool Schemas ──────────────────────────────────────────────────────────
class ExtractionSchema(BaseModel):
    actor: str = Field(description="The main actor performing the action")
    actor_action: str = Field(description="The action taken by the actor")
    actors_reason: str = Field(description="Why the model is asked this, self infer.")
    action_intent: str = Field(description="What the actor is trying to achieve")
    is_trustworthy: bool = Field(description="Whether the actor is trustworthy or not.")
    referable_source: str = Field(
        description="Source justifying the trustworthiness judgment"
    )
    other_actors_reaction: str = Field(
        description="How other actors would likely react"
    )


class EvaluateExtractionSchema(ExtractionSchema):
    input_text: str = Field(description="The original input text that is being parsed.")


# ── 4. Agent Tools ───────────────────────────────────────────────────────────
@tool
def read_input_file() -> str:
    """Reads the input text file and returns its content. Call this first to get context."""
    if not INPUT_FILE.exists():
        return f"Error: Input file not found at {INPUT_FILE}"
    return INPUT_FILE.read_text(encoding="utf-8").strip()


@tool("evaluate_extraction", args_schema=EvaluateExtractionSchema)
def evaluate_extraction(
    actor: str,
    actor_action: str,
    actors_reason: str,
    action_intent: str,
    is_trustworthy: bool,
    referable_source: str,
    other_actors_reaction: str,
    input_text: str,
) -> str:
    """
    Evaluates the extracted intent fields against strict quality rules.
    You MUST call this to verify your extraction before saving.
    Returns 'PASS' if perfect, or a specific actionable critique if flawed.
    """
    eval_prompt = f"""
-You are a **strict, adversarial quality evaluator** for intent extraction.  
-Your job is to find any flaw, ambiguity, or unjustified claim.  
-**Assume worst intent** for any actor whose trustworthiness is not explicitly proven by a credible, verifiable source in the input text.
-Do not use these in input if not strictly necessary -> "_ , / , -"  

Input text: {input_text}

Extracted fields:
- actor: {actor}
- actor_action: {actor_action}
- actors_reason: {actors_reason}
- action_intent: {action_intent}
- is_trustworthy: {is_trustworthy}
- referable_source: {referable_source}
- other_actors_reaction: {other_actors_reaction}

---

### Evaluation rules (apply ALL):
1. **Actor** – Must be a specific entity. Fail if vague or missing.
2. **Actor_action** – Must be a concrete verb phrase. Fail if passive, abstract.
3. **Actors_reason** – The reason why the actor asks this. Fail if identical to action.
4. **Action_intent** – Must describe *why* the action occurred.
5. **is_trustworthy** – `true` only if explicit evidence exists. Assume `false` otherwise.
6. **referable_source** – Must be specific. Fail if empty when true.
7. **other_actors_reaction** – Must be plausible.
8. **Overall consistency** – No logical contradictions.

### Output format:
- **If ALL rules are satisfied**: reply exactly: `PASS`
- **Otherwise**: Write a short critique: `Field "X" fails because ...`
"""
    response = get_llm().invoke(eval_prompt).content.strip()
    return response


@tool("save_final_output", args_schema=ExtractionSchema)
def save_final_output(
    actor: str,
    actor_action: str,
    actors_reason: str,
    action_intent: str,
    is_trustworthy: bool,
    referable_source: str,
    other_actors_reaction: str,
) -> str:
    """
    Saves the finalized intent extraction to the output file.
    Only call this tool AFTER the `evaluate_extraction` tool returns exactly 'PASS'.
    """
    lines = [
        f"Actor            : {actor}",
        f"Action           : {actor_action}",
        f"Actors Reason    : {actors_reason}",
        f"Intent           : {action_intent}",
        f"Is Trustworthy   : {is_trustworthy}",
        f"Source           : {referable_source}",
        f"Other Reaction   : {other_actors_reaction}",
    ]
    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    return f"Success! Output cleanly written to {OUTPUT_FILE}."


# ── 5. Build Custom Graph with ToolNode ───────────────────────────────────────
def build_agent():
    tools = [read_input_file, evaluate_extraction, save_final_output]
    tool_node = ToolNode(tools)
    llm_with_tools = get_llm().bind_tools(tools)

    system_prompt = SystemMessage(
        content="""You are an autonomous Intent Parsing Agent equipped with file and evaluation tools. 
    Your strict workflow is:
    1. Call `read_input_file` to fetch the source text.
    2. Analyze the text and extract the required parameters.
    3. Call `evaluate_extraction` to critique your own extraction.
    4. If critique is given, adjust and call `evaluate_extraction` again.
    5. Only when 'PASS' is returned, call `save_final_output` to save.
    6. Conclude the workflow.
    """
    )

    # Strongly typed Node function
    def call_model(state: AgentState) -> dict[str, list[BaseMessage]]:
        messages = state.messages
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [system_prompt] + messages

        response = llm_with_tools.invoke(messages)
        # Casting to Any is avoided because we are returning the expected dict structure
        return {"messages": [response]}

    # Initialize Graph with the standard TypedDict
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")

    return workflow.compile()


# ── 6. Entry point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    graph = build_agent()

    print("Initiating Tool User Agent Workflow...\n")
    final_state = graph.invoke(
        {
            "messages": [
                (
                    "user",
                    "Start the pipeline: Read the input file, evaluate your intent extraction until it passes, and write to output.",
                )
            ]
        }
    )

    for msg in final_state["messages"]:
        if msg.type == "human" or msg.type == "system":
            continue
        elif msg.type == "ai":
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    print(f"🤖 Agent decided to use tool: [{tc['name']}]")
            else:
                print(f"🤖 Agent thought: {msg.content}")
        elif msg.type == "tool":
            status = "PASS" if msg.content == "PASS" else "CRITIQUE/RESULT"
            print(f"⚙️ Tool Output ({msg.name}): {status}")
            if status != "PASS" and msg.name == "evaluate_extraction":
                print(f"   ↳ {msg.content}")
            print("-" * 40)

    print("\nWorkflow completed. Check Output.txt.")
