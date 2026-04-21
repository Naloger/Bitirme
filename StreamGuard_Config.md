# Stream Guard Node Configuration Guide

This document explains how to configure the `llm_config.json` file for the Stream Guard Node (`node_LoopGuard.py`). The node requires specific configuration values to function properly. All listed fields are mandatory and must be present in the configuration file. If any field is missing, the node will raise a `KeyError`.

## Configuration Structure

The `llm_config.json` file should have the following structure:

```json
{
  "provider": "ollama",
  "ollama": {
    "model": "your-model-name",
    "base_url": "http://127.0.0.1:11434",
    "timeout_seconds": 120,
    "temperature": 0.2,
    "num_ctx": 4096,
    "top_p": 0.9,
    "repeat_penalty": 1.1
  },
  "loop_guard": {
    "max_loops": 2,
    "max_repeated_chunk": 5,
    "repetition_window": 24,
    "pre_content_chunk_limit": 220
  }
}
```

## Field Descriptions

### Top-Level Fields

- **`provider`**: Must be set to `"ollama"`. The node only supports Ollama as the LLM provider.

### `ollama` Section

This section contains configuration for the Ollama API connection and model parameters.

- **`model`**: The name of the Ollama model to use (e.g., `"qwen3.5:0.8b"`, `"llama3.2:3b"`). This is required and should match an installed model in your Ollama instance.
- **`base_url`**: The URL of your Ollama server (default is `"http://127.0.0.1:11434"`). Ensure Ollama is running and accessible at this URL.
- **`timeout_seconds`**: Timeout in seconds for API requests (integer, e.g., `120`). Increase if you have slow responses.
- **`temperature`**: Controls randomness in generation (float between 0.0 and 1.0, e.g., `0.2`). Lower values make output more deterministic.
- **`num_ctx`**: Context window size (integer, e.g., `4096`). Should match your model's context length.
- **`top_p`**: Nucleus sampling parameter (float between 0.0 and 1.0, e.g., `0.9`). Controls diversity of output.
- **`repeat_penalty`**: Penalty for repeating tokens (float, e.g., `1.1`). Helps prevent repetitive text.

### `loop_guard` Section

This section configures the loop detection and prevention mechanisms.

- **`max_loops`**: Maximum number of restart attempts if a loop is detected (integer, e.g., `2`).
- **`max_repeated_chunk`**: Threshold for detecting repeated chunks (integer, e.g., `5`). Lower values are more sensitive to repetition.
- **`repetition_window`**: Number of recent chunks to monitor for repetition (integer, e.g., `24`).
- **`pre_content_chunk_limit`**: Maximum chunks allowed before content starts (integer, e.g., `220`). Prevents models from thinking indefinitely without producing output.

## Notes

- All fields are required. The node will throw an error if any are missing.
- Ensure your Ollama server is running and the specified model is installed.
- Adjust `temperature`, `top_p`, and `repeat_penalty` based on your model's behavior and desired output style.
- The loop guard parameters are tuned for typical use cases but can be adjusted for specific models or tasks.
- If you encounter loops or timeouts, consider increasing `max_loops`, `repetition_window`, or `timeout_seconds`.

## Example Configuration

For a basic setup with a small model:

```json
{
  "provider": "ollama",
  "ollama": {
    "model": "qwen3.5:0.8b",
    "base_url": "http://127.0.0.1:11434",
    "timeout_seconds": 120,
    "temperature": 0.2,
    "num_ctx": 4096,
    "top_p": 0.9,
    "repeat_penalty": 1.1
  },
  "loop_guard": {
    "max_loops": 2,
    "max_repeated_chunk": 5,
    "repetition_window": 24,
    "pre_content_chunk_limit": 220
  }
}
```
