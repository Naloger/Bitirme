from __future__ import annotations

from typing import List, Dict

from langchain_core.messages import BaseMessage, AIMessage


def _messages_to_ollama_format(messages: List[BaseMessage]) -> List[Dict[str, str]]:
    """Convert LangChain messages to Ollama message format."""
    result = []
    for msg in messages:
        if isinstance(msg, AIMessage):
            role = "assistant"
        elif hasattr(msg, "type") and msg.type == "human":
            role = "user"
        elif hasattr(msg, "type") and msg.type == "system":
            role = "system"
        else:
            role = "user"  # default fallback
        content = getattr(msg, "content", str(msg))
        result.append({"role": role, "content": content})
    return result
