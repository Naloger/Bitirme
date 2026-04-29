from __future__ import annotations

import json
import logging
import re
import socket
from collections import Counter, deque
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from pydantic import BaseModel, ConfigDict

from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
    ExtendedModelResponse,
    hook_config,
    wrap_model_call,
)
from langchain.messages import AIMessage
from langchain_core.messages import BaseMessage
from langgraph.runtime import Runtime
from langgraph.types import Command
from typing_extensions import NotRequired

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration Schema
# ---------------------------------------------------------------------------
class StreamGuardConfig(BaseModel):
    """Configuration for StreamGuardMiddleware."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    # Ollama connection
    base_url: str = "http://localhost:11434"
    model: str = "qwen3.5:0.8b"
    timeout_seconds: int = 60

    # Generation parameters
    temperature: float = 0.7
    num_ctx: int = 4096
    top_p: Optional[float] = 0.9
    repeat_penalty: Optional[float] = 1.1

    # Loop guard parameters
    max_loops: int = 2
    max_repeated_chunk: int = 4
    repetition_window: int = 16
    pre_content_chunk_limit: int = 300

    # System prompt
    system_prompt: Optional[str] = None


# ---------------------------------------------------------------------------
# Custom State Schema for Middleware
# ---------------------------------------------------------------------------
class StreamGuardState(AgentState):
    """Extended agent state for stream guard tracking."""

    stream_guard_output: NotRequired[str]
    stream_guard_thinking: NotRequired[str]
    stream_guard_loop_restarts: NotRequired[int]
    stream_guard_model: NotRequired[str]
    stream_guard_success: NotRequired[bool]


# ---------------------------------------------------------------------------
# Core Utilities (Preserved from Original)
# ---------------------------------------------------------------------------
def _normalize_chunk(text: str) -> str:
    """Normalize whitespace and case for stable loop comparison."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _detect_loop(window: deque[str], repetition_limit: int) -> bool:
    """Determine whether the recent chunk window exhibits repetitive behavior."""
    if len(window) < repetition_limit:
        return False

    recent = list(window)[-repetition_limit:]
    if recent[0] and len(set(recent)) == 1:
        return True

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


# ---------------------------------------------------------------------------
# StreamGuardMiddleware: Class-Based Implementation
# ---------------------------------------------------------------------------
class StreamGuardMiddleware(AgentMiddleware):
    """
    LangChain middleware for streaming Ollama output with adaptive loop detection.

    This middleware intercepts model calls via wrap_model_call, manages Ollama
    streaming with loop detection, implements retry logic with feedback prompts,
    and handles reasoning models by separately tracking thinking tokens.

    Attributes:
        config: StreamGuardConfig instance containing connection and guard parameters.
    """

    state_schema = StreamGuardState

    def __init__(self, config: Optional[StreamGuardConfig] = None, **kwargs):
        """Initialize the middleware with optional configuration overrides."""
        super().__init__()
        self.config = config or StreamGuardConfig(**kwargs)

    def _build_ollama_payload(
        self,
        messages: List[Dict[str, str]],
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Construct the Ollama API payload."""
        return {
            "model": self.config.model,
            "messages": messages,
            "stream": True,
            "options": options,
        }

    def _build_generation_options(self) -> Dict[str, Any]:
        """Build generation options from config."""
        options = {
            "temperature": self.config.temperature,
            "num_ctx": self.config.num_ctx,
        }
        if self.config.top_p is not None:
            options["top_p"] = self.config.top_p
        if self.config.repeat_penalty is not None:
            options["repeat_penalty"] = self.config.repeat_penalty
        return options

    def _execute_stream_with_guard(
        self,
        ollama_messages: List[Dict[str, str]],
        options: Dict[str, Any],
    ) -> Tuple[str, str, int, bool]:
        """
        Execute streaming generation with loop detection and retry logic.

        Returns:
            Tuple of (output_text, thinking_text, loop_restarts, success)
        """
        accumulated_output: List[str] = []
        accumulated_thinking: List[str] = []
        loop_count = 0
        max_loops = self.config.max_loops
        repeated_limit = self.config.max_repeated_chunk
        repetition_window = self.config.repetition_window
        pre_content_chunk_limit = self.config.pre_content_chunk_limit

        messages = ollama_messages.copy()

        while True:
            payload = self._build_ollama_payload(messages, options)
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
                    base_url=self.config.base_url,
                    payload=payload,
                    timeout_s=self.config.timeout_seconds,
                ):
                    chunk_count += 1
                    content, thinking, done = _extract_stream_parts(chunk)

                    if content:
                        content_started = True
                        pass_output.append(content)
                        normalized = _normalize_chunk(content)
                        if normalized:
                            chunk_window.append(normalized)
                            if _detect_loop(
                                chunk_window, repetition_limit=repeated_limit
                            ):
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

                        if len(thinking_text_window) >= 8 and _detect_loop(
                            thinking_text_window,
                            repetition_limit=max(3, repeated_limit - 1),
                        ):
                            logger.warning(
                                "Thinking text loop detected at chunk %d", chunk_count
                            )
                            loop_detected = True
                            break

                        if (
                            not content_started
                            and chunk_count >= pre_content_chunk_limit
                        ):
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
                                    "Thinking token stall detected at chunk %d",
                                    chunk_count,
                                )
                                loop_detected = True
                                break

                    if done:
                        stream_done = True
                        logger.info("Stream completed at chunk %d", chunk_count)
                        break

            except (HTTPError, URLError, socket.timeout, Exception) as err:
                logger.error("Ollama stream request failed: %s", err)
                return f"Ollama request failed: {err}", "", loop_count, False

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
                messages.append(
                    {"role": "user", "content": _generate_feedback_prompt()}
                )
                logger.info(
                    "Restarting generation (attempt %d/%d)", loop_count, max_loops
                )
                continue

            if stream_done or not loop_detected or loop_count >= max_loops:
                break

        final_output = "".join(accumulated_output).strip()
        final_thinking = (
            "".join(accumulated_thinking).strip() or "(thinking not available)"
        )

        if not final_output:
            rescued = _salvage_answer_from_thinking("".join(accumulated_thinking))
            if rescued:
                final_output = rescued
                logger.info(
                    "Derived answer from thinking trace via fallback extraction."
                )

        return final_output, final_thinking, loop_count, True

    @hook_config(can_jump_to=["end"])
    def before_model(
        self, state: StreamGuardState, runtime: Runtime
    ) -> Dict[str, Any] | None:
        """
        Node-style hook: Validate configuration before model invocation.

        Returns state updates or jump directive if validation fails.
        """
        if self.config.base_url.startswith("http"):
            return None  # Proceed normally

        logger.error("Invalid Ollama base_url: %s", self.config.base_url)
        return {
            "messages": [
                AIMessage(content="Configuration error: invalid Ollama endpoint.")
            ],
            "stream_guard_success": False,
            "jump_to": "end",
        }

    @wrap_model_call
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ExtendedModelResponse:
        """
        Wrap-style hook: Intercept model call to apply stream guard logic.

        This method bypasses the standard handler and executes Ollama streaming
        directly with loop detection, retry logic, and thinking-token handling.
        """
        # Prepare Ollama-formatted messages from request
        ollama_messages = _messages_to_ollama_format(request.messages)

        # Add/override system prompt if configured
        if self.config.system_prompt:
            # Ensure system message is first
            if ollama_messages and ollama_messages[0]["role"] == "system":
                ollama_messages[0]["content"] = self.config.system_prompt
            else:
                ollama_messages.insert(
                    0, {"role": "system", "content": self.config.system_prompt}
                )

        options = self._build_generation_options()

        # Execute guarded streaming generation
        output_text, thinking_text, loop_restarts, success = (
            self._execute_stream_with_guard(
                ollama_messages=ollama_messages,
                options=options,
            )
        )

        # Construct the model response with guarded output
        response_message = AIMessage(content=output_text)

        # Return ExtendedModelResponse with Command for state updates
        return ExtendedModelResponse(
            model_response=ModelResponse(result=[response_message]),
            command=Command(
                update={
                    "stream_guard_output": output_text,
                    "stream_guard_thinking": thinking_text,
                    "stream_guard_loop_restarts": loop_restarts,
                    "stream_guard_model": self.config.model,
                    "stream_guard_success": success,
                }
            ),
        )

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ExtendedModelResponse:
        """
        Async variant of wrap_model_call.

        Note: Currently delegates to sync implementation. Full async support
        would require aiohttp/httpx integration for Ollama streaming.
        """
        # Delegate to sync implementation for now
        return self.wrap_model_call(request, handler)


# ---------------------------------------------------------------------------
# Decorator-Based Alternative (Simpler Use Case)
# ---------------------------------------------------------------------------
def create_stream_guard_decorator(
    config: Optional[StreamGuardConfig] = None,
    **kwargs,
):
    """
    Factory for decorator-based stream guard middleware.

    Use for simple, single-hook scenarios. For complex configuration,
    prefer the class-based StreamGuardMiddleware.
    """
    cfg = config or StreamGuardConfig(**kwargs)

    @wrap_model_call
    def stream_guard_wrapper(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ExtendedModelResponse:
        # Instantiate middleware internally to reuse logic
        mware = StreamGuardMiddleware(config=cfg)
        return mware.wrap_model_call(request, handler)

    return stream_guard_wrapper


# ---------------------------------------------------------------------------
# Factory Function for Convenient Instantiation
# ---------------------------------------------------------------------------
def create_stream_guard_middleware(
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    max_loops: Optional[int] = None,
    **config_kwargs,
) -> StreamGuardMiddleware:
    """
    Factory function to create a StreamGuardMiddleware instance.

    Args:
        model: Ollama model name to use.
        base_url: Ollama API base URL.
        max_loops: Maximum retry attempts on loop detection.
        **config_kwargs: Additional StreamGuardConfig parameters.

    Returns:
        Configured StreamGuardMiddleware instance.
    """
    config_params = {}
    if model is not None:
        config_params["model"] = model
    if base_url is not None:
        config_params["base_url"] = base_url
    if max_loops is not None:
        config_params["max_loops"] = max_loops
    config_params.update(config_kwargs)
    return StreamGuardMiddleware(config=StreamGuardConfig(**config_params))


# ---------------------------------------------------------------------------
# Example Usage
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
        middleware = create_stream_guard_middleware(
            model="qwen3.5:0.8b",
            base_url="http://localhost:11434",
            max_loops=3,
            system_prompt="Be concise and avoid repetitive output.",
        )
        output_text, thinking_text, loop_restarts, success = (
            middleware._execute_stream_with_guard(  # type: ignore[attr-defined]
                ollama_messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.7, "num_ctx": 4096},
            )
        )
        report = [
            "provider=ollama",
            f"model={middleware.config.model}",
            f"loop_restarts={loop_restarts}",
            f"success={success}",
            "",
            "[assistant_output]",
            output_text,
            "",
            "[thinking_output]",
            thinking_text,
        ]
        output_file.write_text("\n".join(report).strip() + "\n", encoding="utf-8")
        logger.info("Processed: %s -> %s", input_file, output_file)
    else:
        logger.error("Input file not found: %s", input_file)
