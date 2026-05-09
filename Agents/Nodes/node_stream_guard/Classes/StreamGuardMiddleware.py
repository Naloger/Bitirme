from __future__ import annotations

import socket
from collections import deque
from typing import Optional, List, Dict, Any, Tuple, Callable
from urllib.error import HTTPError, URLError

from langchain.agents.middleware import (
    AgentMiddleware,
    hook_config,
    wrap_model_call,
    ModelRequest,
    ModelResponse,
    ExtendedModelResponse,
)
from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime
from langgraph.types import Command

from Agents.Nodes.node_stream_guard.Functions._detect_loop import _detect_loop
from Agents.Nodes.node_stream_guard.Functions._extract_stream_parts import (
    _extract_stream_parts,
)
from Agents.Nodes.node_stream_guard.Functions._generate_feedback_prompt import (
    _generate_feedback_prompt,
)
from Agents.Nodes.node_stream_guard.Functions._messages_to_ollama_format import (
    _messages_to_ollama_format,
)
from Agents.Nodes.node_stream_guard.Functions._normalize_chunk import _normalize_chunk
from Agents.Nodes.node_stream_guard.Functions._salvage_answer_from_thinking import (
    _salvage_answer_from_thinking,
)
from Agents.Nodes.node_stream_guard.Functions._stream_chat_once import _stream_chat_once
from Agents.Nodes.node_stream_guard.node_LoopGuard import StreamGuardState, logger
from Agents.Nodes.node_stream_guard.Classes.StreamGuardConfig import StreamGuardConfig


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
