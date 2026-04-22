# Stream Guard Node - Code Explanation

This document explains the `node.py` file, which implements a stream-guarded LangGraph node for Ollama LLM interactions.

## Overview

The code provides a LangGraph node that:
1. Reads a prompt from state `input_text`
2. Streams assistant output via Ollama API
3. Detects loops in streamed chunks and cuts off when needed
4. Feeds a compact thinking summary back to the model to continue
5. Returns the result in state `output_text`

## Architecture

### Key Components

| Component | Purpose |
|-----------|---------|
| `StreamGuardState` | Pydantic model for state management |
| `stream_guard_node` | Main LangGraph node function |
| `create_stream_guard_graph` | Creates the StateGraph |

### State Model

```python
class StreamGuardState(BaseModel):
    input_text: str = ""      # User prompt
    output_text: str = ""     # Model response
    thinking_text: str = ""   # Reasoning trace
    loop_restarts: int = 0    # Restart count
    model: str = ""           # Model name
    messages: List[Dict] = [] # Chat history
```

## Loop Detection

The system uses two detection strategies:

### 1. Content-Based Loop Detection

- Monitors normalized chunks in a sliding window
- Triggers on same-chunk repetition (configurable via `repeated_limit`)
- Also detects repeated n-gram patterns (5-grams by default)

### 2. Thinking-Only Loop Detection

**Important Fix Applied:**
- Guarded on `content_started` flag
- Prevents false-positive cutoff for reasoning models like gemma4
- Only activates after first content token appears

The detection includes:
- Repeated thinking text patterns (qwen often loops here)
- Hard-stop if model thinks too long before content (`pre_content_chunk_limit`)
- Legacy short-thinking detector after content starts

## Stream Processing

### Chunk Extraction

`_extract_stream_parts()` handles different response formats:
- Standard: `message.content`, `message.thinking`
- Alternative: `response`, `thinking_output` keys
- Returns `(content, thinking, done)` tuple

### Retry Mechanism

When loop detected:
1. Increments `loop_count`
2. Appends assistant message with partial output
3. Sends feedback prompt asking for direct answer
4. Retries up to `max_loops` times

### Feedback Prompt

Important: Does NOT inject thinking content back. This prevents re-triggering reasoning chains in models like gemma4, qwq, deepseek-r1.

```python
"Your previous response was cut short due to repetition. 
Output only the final answer now, directly and concisely. 
Do not reason or think step-by-step — just answer."
```

## Fallback Extraction

If model only emits thinking (no content), `_fallback_answer_from_thinking()` attempts to extract:
1. Draft markers: `* Draft N: ...`
2. First substantial sentence (40+ chars)

## Configuration

Loaded from `llm_config` module:

| Config Key | Default | Description |
|------------|---------|-------------|
| `model` | `qwen3.5:0.8b` | Ollama model |
| `base_url` | `http://127.0.0.1:11434` | API endpoint |
| `timeout_seconds` | 120 | Request timeout |
| `temperature` | 0.2 | Sampling temperature |
| `num_ctx` | 4096 | Context window |
| `max_loops` | 2 | Max restarts |
| `repeated_limit` | 5 | Repetition threshold |
| `repetition_window` | 24 | Sliding window size |
| `pre_content_chunk_limit` | 220 | Max thinking chunks |

## Usage

```python
# As LangGraph node
graph = create_stream_guard_graph()
app = graph.compile()

# Direct invocation
test_state = StreamGuardState(input_text="Your prompt")
result = stream_guard_node(test_state)
```

## Fixes Applied

1. **Thinking-only loop detection** - Now gated on `content_started` flag to prevent false positives for reasoning models
2. **Restart skip** - Skipped entirely if loop fired before any content was produced
3. **Feedback prompt** - No longer re-injects thinking to avoid re-triggering reasoning chains