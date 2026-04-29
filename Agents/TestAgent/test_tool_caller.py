from __future__ import annotations

import sys
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver

from Tools import util_tools
from support_lib.load_llm import load_llm



PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))



@tool
def current_datetime() -> dict[str, str]:
    """Return the current local date and time."""
    return util_tools.get_datetime()


@tool
def web_search(query,max_results=5 ) -> list[dict[str, str]]:
    """Return the current local date and time."""
    return util_tools.duckduckgo_search(query,max_results)

def build_agent():
    llm = load_llm()
    return create_agent(
        model=llm,
        tools=[current_datetime,web_search],
        system_prompt=(
            "You are a helpful assistant. "
        ),
        checkpointer=MemorySaver(),
    )


def run_once(user_input: str) -> str:
    agent = build_agent()
    config: RunnableConfig = {"configurable": {"thread_id": "test_tool_caller"}}
    result = agent.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
    )

    messages = result.get("messages", [])
    if not messages:
        return "No response from agent."

    last_message = messages[-1]
    content = getattr(last_message, "content", "")
    if isinstance(content, list):
        return "\n".join(str(part) for part in content)
    return str(content)


def main() -> None:
    print("LangChain Tool-Calling Test Agent")
    prompt = input("Enter your prompt: ").strip()

    print("\n[User Input]")
    print(prompt)

    output = run_once(prompt)

    print("\n[Agent Output]")
    print(output)


if __name__ == "__main__":
    main()
