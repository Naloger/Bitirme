from __future__ import annotations

import json
import logging
import re
import socket
from collections import Counter, deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END

# Local imports (ensure project root is in sys.path prior to execution)
try:
    from llm_config import ConfigError, load_llm_config  # noqa: E402
except ImportError as err:
    raise ImportError(
        "Failed to import llm_config. Ensure project root is in sys.path."
    ) from err

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State Schema
# ---------------------------------------------------------------------------
class StreamGuardState(BaseModel):
    """LangGraph-compatible state schema for the stream-guard node."""

    input_text: str = ""
    output_text: str = ""
    thinking_text: str = ""
    loop_restarts: int = 0
    model: str = ""
    messages: List[Dict[str, str]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Core Utilities
# ---------------------------------------------------------------------------
def _normalize_chunk(text: str) -> str:
    """Normalize whitespace and case for stable loop comparison."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _detect_loop(window: deque[str], repetition_limit: int) -> bool:
    """Determine whether the recent chunk window exhibits repetitive behavior."""
    if len(window) < repetition_limit:
        return False

    # Exact recent-chunk repetition (catches immediate stalling)
    recent = list(window)[-repetition_limit:]
    if recent[0] and len(set(recent)) == 1:
        return True

    # N-gram token repetition over the accumulated window
    text = " ".join(window)
    tokens = text.split()
    if len(tokens) < 12:
        return False

    n = 5
    ngrams = [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]
    if not ngrams:
        return False

    most_common_ngram, count = Counter(ngrams).most_common(1)[0]
    threshold = max(3, repetition_limit - 1)
    return count >= threshold


def _extract_stream_parts(chunk: Dict[str, Any]) -> Tuple[str, str, bool]:
    """Extract content, thinking, and completion status from an Ollama stream chunk."""
    if not isinstance(chunk, dict):
        return "", "", False

    message = chunk.get("message")
    content = ""
    thinking = ""

    if isinstance(message, dict):
        content = str(message.get("content", "") or "")
        thinking = str(message.get("thinking", "") or "") or str(
            message.get("thinking_output", "") or ""
        )

    if not content:
        content = str(chunk.get("response", "") or "")
    if not thinking:
        thinking = str(chunk.get("thinking", "") or "")

    done = bool(chunk.get("done", False))
    return content, thinking, done


def _stream_chat_once(
    base_url: str, payload: Dict[str, Any], timeout_s: int
) -> Iterable[Dict[str, Any]]:
    """Yield parsed JSON objects from an Ollama streaming endpoint."""
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(req, timeout=timeout_s) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                yield parsed


def _generate_feedback_prompt() -> str:
    """Return a concise instruction to halt reasoning and produce a direct answer."""
    return (
        "Your previous response was interrupted due to excessive repetition. "
        "Provide only the final answer now, directly and concisely. "
        "Do not reason, think step-by-step, or output chain-of-thought tokens."
    )


def _salvage_answer_from_thinking(thinking_text: str) -> str:
    """Attempt to extract a coherent final answer from reasoning traces."""
    if not thinking_text:
        return ""

    draft_matches = re.findall(
        r"\*\s*Draft\s*\d+\s*:\s*([^\n]+)", thinking_text, flags=re.IGNORECASE
    )
    if draft_matches:
        candidate = draft_matches[-1].strip().strip('"')
        if candidate:
            return candidate.rstrip(" .") + "."

    flat = re.sub(r"\s+", " ", thinking_text).strip()
    parts = re.split(r"(?<=[.!?])\s+", flat)
    for part in parts:
        text = part.strip().strip('"')
        if len(text) >= 40 and "thinking process" not in text.lower():
            return text.rstrip(" .") + "."

    return ""


# ---------------------------------------------------------------------------
# LangGraph Node
# ---------------------------------------------------------------------------
def stream_guard_node(state: StreamGuardState) -> Dict[str, Any]:
    """
    LangGraph node that streams Ollama output with adaptive loop detection.

    Handles reasoning models by deferring loop detection until content tokens
    appear, prevents thinking-token injection on retry, and salvages partial
    outputs when necessary.
    """
    if not state.input_text:
        return {
            "output_text": "Input is empty.",
            "thinking_text": "",
            "loop_restarts": 0,
        }

    try:
        cfg = load_llm_config()
    except (ConfigError, json.JSONDecodeError, Exception) as err1:
        logger.error("Configuration load failed: %s", err1)
        return {
            "output_text": f"Configuration error: {err1}",
            "thinking_text": "",
            "loop_restarts": 0,
        }

    if cfg.provider != "ollama":
        return {
            "output_text": "Unsupported provider. Only 'ollama' is permitted.",
            "thinking_text": "",
            "loop_restarts": 0,
        }

    ollama_cfg = cfg.raw.get("ollama", {})
    loop_cfg = cfg.raw.get("loop_guard", {})

    model = state.model or ollama_cfg.get("model", "llama3.2")
    base_url = ollama_cfg.get("base_url", "http://localhost:11434")
    timeout_s = int(ollama_cfg.get("timeout_seconds", 60))
    temperature = float(ollama_cfg.get("temperature", 0.7))
    num_ctx = int(ollama_cfg.get("num_ctx", 4096))
    top_p = (
        float(ollama_cfg.get("top_p", 0.9))
        if ollama_cfg.get("top_p") is not None
        else None
    )
    repeat_penalty = (
        float(ollama_cfg.get("repeat_penalty", 1.1))
        if ollama_cfg.get("repeat_penalty") is not None
        else None
    )

    max_loops = int(loop_cfg.get("max_loops", 2))
    repeated_limit = int(loop_cfg.get("max_repeated_chunk", 4))
    repetition_window = int(loop_cfg.get("repetition_window", 16))
    pre_content_chunk_limit = int(loop_cfg.get("pre_content_chunk_limit", 150))

    # Initialize conversation history
    messages: List[Dict[str, str]] = state.messages or [
        {
            "role": "system",
            "content": "Be concise, avoid repetitive output, and complete the task in one coherent answer.",
        },
        {"role": "user", "content": state.input_text},
    ]

    accumulated_output: List[str] = []
    accumulated_thinking: List[str] = []
    loop_count = 0

    logger.info(
        "Stream guard initialized: model=%s, max_loops=%s, repeated_limit=%s",
        model,
        max_loops,
        repeated_limit,
    )

    while True:
        options: Dict[str, Any] = {
            "temperature": temperature,
            "num_ctx": num_ctx,
        }
        if top_p is not None:
            options["top_p"] = top_p
        if repeat_penalty is not None:
            options["repeat_penalty"] = repeat_penalty

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": options,
        }

        chunk_window: deque[str] = deque(maxlen=max(8, repetition_window))
        thinking_window: deque[int] = deque(maxlen=20)
        thinking_text_window: deque[str] = deque(maxlen=max(8, repetition_window))

        pass_output: List[str] = []
        pass_thinking: List[str] = []
        stream_done = False
        loop_detected = False
        content_started = False

        try:
            chunk_count = 0
            for chunk in _stream_chat_once(
                base_url=base_url, payload=payload, timeout_s=timeout_s
            ):
                chunk_count += 1
                content, thinking, done = _extract_stream_parts(chunk)

                if content:
                    content_started = True
                    pass_output.append(content)
                    normalized = _normalize_chunk(content)
                    if normalized:
                        chunk_window.append(normalized)
                        if _detect_loop(chunk_window, repetition_limit=repeated_limit):
                            logger.warning(
                                "Content loop detected at chunk %d", chunk_count
                            )
                            loop_detected = True
                            break

                if not content and thinking:
                    pass_thinking.append(thinking)
                    thinking_window.append(len(thinking))
                    normalized_thinking = _normalize_chunk(thinking)
                    if normalized_thinking:
                        thinking_text_window.append(normalized_thinking)

                    # Thinking-only loop detection (gated post-content-start or early-hard-stop)
                    if len(thinking_text_window) >= 8 and _detect_loop(
                        thinking_text_window,
                        repetition_limit=max(3, repeated_limit - 1),
                    ):
                        logger.warning(
                            "Thinking text loop detected at chunk %d", chunk_count
                        )
                        loop_detected = True
                        break

                    if not content_started and chunk_count >= pre_content_chunk_limit:
                        logger.warning(
                            "Pre-content chunk limit reached (%d)",
                            pre_content_chunk_limit,
                        )
                        loop_detected = True
                        break

                    if (
                        content_started
                        and len(thinking_window) >= 20
                        and chunk_count > 50
                    ):
                        avg_len = sum(thinking_window) / len(thinking_window)
                        max_recent = max(list(thinking_window)[-10:])
                        if avg_len < 12 and max_recent < 15:
                            logger.warning(
                                "Thinking token stall detected at chunk %d", chunk_count
                            )
                            loop_detected = True
                            break

                if done:
                    stream_done = True
                    logger.info("Stream completed at chunk %d", chunk_count)
                    break

        except (HTTPError, URLError, socket.timeout, Exception) as err2:
            logger.error("Ollama stream request failed: %s", err2)
            return {
                "output_text": f"Ollama request failed: {err2}",
                "thinking_text": "",
                "loop_restarts": loop_count,
                "model": model,
            }

        accumulated_output.extend(pass_output)
        accumulated_thinking.extend(pass_thinking)

        if loop_detected and loop_count < max_loops:
            loop_count += 1
            assistant_seed = (
                "".join(pass_output).strip()
                if pass_output
                else "(no content emitted yet)"
            )
            messages.append({"role": "assistant", "content": assistant_seed})
            messages.append({"role": "user", "content": _generate_feedback_prompt()})
            logger.info("Restarting generation (attempt %d/%d)", loop_count, max_loops)
            continue

        if stream_done or not loop_detected or loop_count >= max_loops:
            break

    final_output = "".join(accumulated_output).strip()
    final_thinking = "".join(accumulated_thinking).strip() or "(thinking not available)"

    if not final_output:
        rescued = _salvage_answer_from_thinking("".join(accumulated_thinking))
        if rescued:
            final_output = rescued
            logger.info("Derived answer from thinking trace via fallback extraction.")

    logger.info(
        "Node completed: loops=%d, output_len=%d", loop_count, len(final_output)
    )
    return {
        "output_text": final_output,
        "thinking_text": final_thinking,
        "loop_restarts": loop_count,
        "model": model,
    }


# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------
def create_stream_guard_graph() -> StateGraph[StreamGuardState]:
    """Construct and return the LangGraph workflow for stream-guarded generation."""
    graph = StateGraph(state_schema=StreamGuardState)
    graph.add_node("stream_guard", stream_guard_node)
    graph.add_edge(START, "stream_guard")
    graph.add_edge("stream_guard", END)
    return graph


# ---------------------------------------------------------------------------
# CLI / Test Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s"
    )
    base_path = Path(__file__).parent
    input_file = base_path / "Input.txt"
    output_file = base_path / "Output.txt"

    if input_file.exists():
        prompt = input_file.read_text(encoding="utf-8").strip()
        initial_state = StreamGuardState(input_text=prompt)
        result = stream_guard_node(initial_state)

        report = [
            "provider=ollama",
            f"model={result.get('model', '')}",
            f"loop_restarts={result.get('loop_restarts', 0)}",
            "",
            "[assistant_output]",
            result.get("output_text", ""),
            "",
            "[thinking_output]",
            result.get("thinking_text", ""),
        ]
        output_file.write_text("\n".join(report).strip() + "\n", encoding="utf-8")
        logger.info("Processed: %s -> %s", input_file, output_file)
    else:
        logger.error("Input file not found: %s", input_file)


