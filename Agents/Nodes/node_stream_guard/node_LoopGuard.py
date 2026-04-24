"""Stream-guarded Ollama LangGraph node.

- Reads prompt from state input_text
- Streams assistant output and optional thinking tokens via Ollama
- Detects loops in streamed chunks and cuts off when needed
- Feeds a compact thinking summary back to the model to continue
- Returns result in state output_text

Fixes applied:
- Thinking-only loop detection now gated on content_started flag
  (prevents false-positive cutoff for reasoning models like gemma4)
- Restart skipped entirely if loop fired before any content was produced
- Feedback prompt no longer re-injects thinking (avoids re-triggering
  the reasoning chain on restart)
"""

from __future__ import annotations

from collections import Counter, deque
import json
from pathlib import Path
import re
import sys
from typing import Any, Deque, Dict, Iterable, List, Tuple
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm_config import ConfigError, load_llm_config  # noqa: E402

# Module-level flag for debug logging
_debug_logged = False


class StreamGuardState(BaseModel):
    """State for stream guard node processing."""

    input_text: str = ""
    output_text: str = ""
    thinking_text: str = ""
    loop_restarts: int = 0
    model: str = ""
    messages: List[Dict[str, str]] = Field(default_factory=list)


def _normalize_chunk(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _is_looping(chunk_window: Deque[str], repeated_limit: int) -> bool:
    if not chunk_window:
        return False

    # Direct same-chunk repetition, catches common model stalls early.
    last = chunk_window[-1]
    if last and list(chunk_window)[-repeated_limit:].count(last) >= repeated_limit:
        print(
            f"[LOOP] Detected same-chunk repetition: '{last[:40]}...'", file=sys.stderr
        )
        return True

    joined = " ".join(chunk_window)
    tokens = joined.split()
    if len(tokens) < 12:
        return False

    # Detect repeated 5-gram patterns in the recent window.
    n = 5
    ngrams = [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]
    if not ngrams:
        return False
    top_ngram, top_count = Counter(ngrams).most_common(1)[0]
    threshold = max(3, repeated_limit - 1)
    if top_count >= threshold:
        print(
            f"[LOOP] Detected n-gram repetition: {top_ngram} appears {top_count}x "
            f"(threshold={threshold})",
            file=sys.stderr,
        )
        return True
    return False


def _extract_stream_parts(chunk: Dict[str, object]) -> Tuple[str, str, bool]:
    message = chunk.get("message") if isinstance(chunk, dict) else None
    content = ""
    thinking = ""

    if isinstance(message, dict):
        content = str(message.get("content", "") or "")
        thinking = str(message.get("thinking", "") or "")

    # Fallbacks for models/proxies that emit different keys.
    if not content:
        content = (
            str(chunk.get("response", "") or "") if isinstance(chunk, dict) else ""
        )
    if not thinking:
        thinking = (
            str(chunk.get("thinking", "") or "") if isinstance(chunk, dict) else ""
        )
        # Also check within message for nested thinking (some API versions).
        if isinstance(message, dict) and not thinking:
            thinking = str(message.get("thinking_output", "") or "")

    done = bool(chunk.get("done", False)) if isinstance(chunk, dict) else False

    # Debug: log chunk structure on first non-empty chunk.
    global _debug_logged
    if (content or thinking) and not _debug_logged:
        print(f"[DEBUG] First chunk keys: {list(chunk.keys())}", file=sys.stderr)
        if isinstance(message, dict):
            print(f"[DEBUG] Message keys: {list(message.keys())}", file=sys.stderr)
        _debug_logged = True

    return content, thinking, done


def _stream_chat_once(
    base_url: str, payload: Dict[str, object], timeout_s: int
) -> Iterable[Dict[str, object]]:
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


def _thinking_feedback_prompt() -> str:
    # NOTE: We deliberately do NOT feed the thinking content back here.
    # Reasoning models (e.g. gemma4, qwq, deepseek-r1) treat injected
    # thinking text as a cue to re-enter their chain-of-thought loop,
    # which causes the exact nested repetition we are trying to fix.
    # Asking for a direct answer only avoids re-triggering the reasoning phase.
    return (
        "Your previous response was cut short due to repetition. "
        "Output only the final answer now, directly and concisely. "
        "Do not reason or think step-by-step — just answer."
    )


def _fallback_answer_from_thinking(thinking_text: str) -> str:
    """Extract a usable one-sentence answer if model emitted only thinking."""
    if not thinking_text:
        return ""

    # Prefer explicit draft lines, usually the best candidate in reasoning traces.
    draft_matches = re.findall(
        r"\*\s*Draft\s*\d+\s*:\s*([^\n]+)", thinking_text, flags=re.IGNORECASE
    )
    if draft_matches:
        candidate = draft_matches[-1].strip().strip('"')
        if candidate:
            return candidate.rstrip(" .") + "."

    # Fallback: pick first substantial sentence-like fragment.
    flat = re.sub(r"\s+", " ", thinking_text).strip()
    parts = re.split(r"(?<=[.!?])\s+", flat)
    for part in parts:
        text = part.strip().strip('"')
        if len(text) >= 40 and "thinking process" not in text.lower():
            return text.rstrip(" .") + "."

    return ""


def stream_guard_node(state: StreamGuardState) -> dict[str, Any]:
    """LangGraph node for stream-guarded LLM generation with loop detection."""

    if not state.input_text:
        return {
            "output_text": "Input is empty.",
            "thinking_text": "",
            "loop_restarts": 0,
        }

    try:
        cfg = load_llm_config()
    except (ConfigError, json.JSONDecodeError) as exc:
        return {
            "output_text": f"Config error: {exc}",
            "thinking_text": "",
            "loop_restarts": 0,
        }

    if cfg.provider != "ollama":
        return {
            "output_text": "Only ollama provider is supported.",
            "thinking_text": "",
            "loop_restarts": 0,
        }

    ollama_cfg = cfg.raw["ollama"]
    loop_cfg = cfg.raw["loop_guard"]

    model = state.model or ollama_cfg["model"]
    base_url = ollama_cfg["base_url"]
    timeout_seconds = int(ollama_cfg["timeout_seconds"])
    temperature = float(ollama_cfg["temperature"])
    num_ctx = int(ollama_cfg["num_ctx"])
    top_p = ollama_cfg["top_p"]
    repeat_penalty = ollama_cfg["repeat_penalty"]

    max_loops = int(loop_cfg["max_loops"])
    repeated_limit = int(loop_cfg["max_repeated_chunk"])
    repetition_window = int(loop_cfg["repetition_window"])
    pre_content_chunk_limit = int(loop_cfg["pre_content_chunk_limit"])

    input_prompt = state.input_text

    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "Be concise, avoid repetitive output, and complete the task "
                "in one coherent answer."
            ),
        },
        {"role": "user", "content": input_prompt},
    ]

    accumulated_output = ""
    accumulated_thinking = ""
    loop_count = 0

    print(
        f"[START] LangGraph node with model={model}, max_loops={max_loops}, "
        f"repeated_limit={repeated_limit}",
        file=sys.stderr,
    )
    print(f"[CONFIG] base_url={base_url}, timeout={timeout_seconds}s", file=sys.stderr)
    print(f"[PROMPT] Input: {input_prompt[:100]}...", file=sys.stderr)

    while True:
        options: Dict[str, float | int] = {
            "temperature": temperature,
            "num_ctx": num_ctx,
        }
        if top_p is not None:
            options["top_p"] = float(top_p)
        if repeat_penalty is not None:
            options["repeat_penalty"] = float(repeat_penalty)

        payload: Dict[str, object] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": options,
        }

        chunk_window: Deque[str] = deque(maxlen=max(8, repetition_window))
        thinking_window: Deque[int] = deque(maxlen=20)
        thinking_text_window: Deque[str] = deque(maxlen=max(8, repetition_window))
        pass_output = ""
        pass_thinking = ""
        stream_done = False
        loop_detected = False

        # FIX: Track whether the model has started emitting content tokens yet.
        # Reasoning models (gemma4, qwq, deepseek-r1, etc.) stream their entire
        # chain-of-thought *before* any content appears.  The old thinking-only
        # loop detector fired during this normal thinking phase, cutting the
        # stream before the answer was ever produced.  We now only engage that
        # detector once content has started flowing.
        content_started = False

        try:
            chunk_count = 0
            for chunk in _stream_chat_once(
                base_url=base_url, payload=payload, timeout_s=timeout_seconds
            ):
                chunk_count += 1
                content, thinking, done = _extract_stream_parts(chunk)

                if chunk_count % 10 == 0:
                    print(
                        f"[STREAM] Chunk {chunk_count}: content_len={len(content)}, "
                        f"thinking_len={len(thinking)}, done={done}",
                        file=sys.stderr,
                    )

                pass_output += content
                pass_thinking += thinking

                # --- Content loop detection (unchanged) ---
                if content:
                    content_started = True
                    normalized = _normalize_chunk(content)
                    if normalized:
                        chunk_window.append(normalized)
                        if _is_looping(chunk_window, repeated_limit=repeated_limit):
                            print(
                                f"[LOOP] Breaking stream at chunk {chunk_count} "
                                "(content loop detected)",
                                file=sys.stderr,
                            )
                            loop_detected = True
                            break

                # --- Thinking-only loop detection ---
                # FIX: Guard on content_started so we never interrupt a model
                # that is still in its pure reasoning / chain-of-thought phase.
                if not content and thinking:
                    thinking_window.append(len(thinking))
                    normalized_thinking = _normalize_chunk(thinking)
                    if normalized_thinking:
                        thinking_text_window.append(normalized_thinking)

                    # Detect repeated thinking text patterns (qwen often loops here before content).
                    if len(thinking_text_window) >= 8 and _is_looping(
                        thinking_text_window, repeated_limit=max(3, repeated_limit - 1)
                    ):
                        print(
                            f"[LOOP] Breaking stream at chunk {chunk_count} (thinking text loop)",
                            file=sys.stderr,
                        )
                        loop_detected = True
                        break

                    # Hard-stop if model keeps thinking for too long before first content token.
                    if not content_started and chunk_count >= pre_content_chunk_limit:
                        print(
                            f"[LOOP] Breaking stream at chunk {chunk_count} (no content before limit={pre_content_chunk_limit})",
                            file=sys.stderr,
                        )
                        loop_detected = True
                        break

                    # Keep legacy short-thinking detector after content started.
                    if (
                        content_started
                        and len(thinking_window) >= 20
                        and chunk_count > 50
                    ):
                        avg_thinking_len = sum(thinking_window) / len(thinking_window)
                        if avg_thinking_len < 12:
                            recent_lengths = list(thinking_window)[-10:]
                            max_recent = max(recent_lengths)
                            if max_recent < 15:
                                print(
                                    f"[LOOP] Breaking stream at chunk {chunk_count} "
                                    f"(thinking-only loop: avg_len={avg_thinking_len:.1f}, "
                                    f"max_recent={max_recent})",
                                    file=sys.stderr,
                                )
                                loop_detected = True
                                break

                if done:
                    stream_done = True
                    print(
                        f"[STREAM] Stream complete at chunk {chunk_count} "
                        f"(total_content={len(pass_output)}, "
                        f"total_thinking={len(pass_thinking)})",
                        file=sys.stderr,
                    )
                    break

        except (HTTPError, URLError, TimeoutError) as exc:
            return {
                "output_text": (
                    f"Ollama request failed: {exc}\n\n"
                    "Make sure Ollama is running:\n  ollama serve"
                ),
                "thinking_text": "",
                "loop_restarts": loop_count,
                "model": model,
            }

        accumulated_output += pass_output
        accumulated_thinking += pass_thinking

        if loop_detected and loop_count < max_loops:
            loop_count += 1

            # If no content yet, still retry once with a strict direct-answer instruction.
            assistant_seed = (
                pass_output if pass_output.strip() else "(no content emitted yet)"
            )
            feedback = _thinking_feedback_prompt()
            messages.append({"role": "assistant", "content": assistant_seed})
            messages.append({"role": "user", "content": feedback})
            print(
                f"[LOOP] Restarting generation #{loop_count} with feedback",
                file=sys.stderr,
            )
            continue

        if stream_done or not loop_detected or loop_count >= max_loops:
            break

    print(
        f"Stream guard node completed: loop_restarts={loop_count}, "
        f"output_len={len(accumulated_output)}",
        file=sys.stderr,
    )

    final_output = accumulated_output.strip()
    final_thinking = accumulated_thinking.strip() or "(thinking not available)"

    # If model never emitted content, salvage one concise sentence from thinking.
    if not final_output:
        rescued = _fallback_answer_from_thinking(accumulated_thinking)
        if rescued:
            final_output = rescued
            print("[FALLBACK] Derived answer from thinking trace.", file=sys.stderr)

    return {
        "output_text": final_output,
        "thinking_text": final_thinking,
        "loop_restarts": loop_count,
        "model": model,
    }


def create_stream_guard_graph() -> StateGraph[StreamGuardState]:
    """Create and return the stream guard LangGraph."""
    graph = StateGraph(state_schema=StreamGuardState)
    graph.add_node("stream_guard", stream_guard_node)
    graph.add_edge(START, "stream_guard")
    graph.add_edge("stream_guard", END)
    return graph


if __name__ == "__main__":
    BASE = Path(__file__).parent
    INPUT = BASE / "Input.txt"
    OUTPUT = BASE / "Output.txt"

    if INPUT.exists():
        test_prompt = INPUT.read_text(encoding="utf-8").strip()
        test_state = StreamGuardState(input_text=test_prompt)
        result = stream_guard_node(test_state)

        output_lines = [
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
        OUTPUT.write_text("\n".join(output_lines).strip() + "\n", encoding="utf-8")
        print(f"Stream guard node processed: {INPUT} -> {OUTPUT}")
    else:
        print(f"Input file not found: {INPUT}")
