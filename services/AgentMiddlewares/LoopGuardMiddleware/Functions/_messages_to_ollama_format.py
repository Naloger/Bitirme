from __future__ import annotations

from typing import List, Dict, Any


def _messages_to_ollama_format(messages: List[Any]) -> List[Dict[str, str]]:
    """Convert a variety of message types to Ollama message format.

    This function is intentionally flexible so the middleware does not
    require LangChain at runtime. It accepts:
      - dicts with keys ('role','content') or ('type','content')
      - objects with attributes 'type' and 'content'
      - simple strings (treated as user content)

    The role mapping is:
      - assistant / ai -> 'assistant'
      - human / user -> 'user'
      - system -> 'system'
      - default -> 'user'
    """
    result: List[Dict[str, str]] = []
    for msg in messages or []:
        role = "user"
        content = ""

        # dict-like messages (preferred)
        if isinstance(msg, dict):
            # allow 'role' or 'type' keys
            role_key = msg.get("role") or msg.get("type")
            if isinstance(role_key, str):
                role_lc = role_key.lower()
                if role_lc in ("assistant", "ai"):
                    role = "assistant"
                elif role_lc in ("system",):
                    role = "system"
                else:
                    role = "user"
            content = str(msg.get("content", "") or "")

        else:
            # object-like messages with attributes
            if hasattr(msg, "content"):
                content = str(getattr(msg, "content") or "")
            else:
                # fallback: str(msg)
                content = str(msg or "")

            if hasattr(msg, "type"):
                t = getattr(msg, "type")
                try:
                    t_lc = str(t).lower()
                except Exception:
                    t_lc = ""
                if t_lc in ("assistant", "ai"):
                    role = "assistant"
                elif t_lc in ("system",):
                    role = "system"
                else:
                    role = "user"

        result.append({"role": role, "content": content})

    return result
