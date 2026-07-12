import requests
import json
import traceback

from Config import config


def call_llm(prompt: str, system_prompt: str | None = None) -> str:
    """
    Call the configured LLM server (Ollama/OpenAI compatible) with the given prompt.
    Raises errors directly if execution or connection fails.
    """
    url = (
        f"{config.BASE_URL}/chat/completions"
        if config.BASE_URL
        else "http://localhost:11434/v1/chat/completions"
    )
    headers = {"Content-Type": "application/json"}
    if config.API_KEY:
        headers["Authorization"] = f"Bearer {config.API_KEY}"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": config.MODEL,
        "messages": messages,
        "temperature": config.TEMPERATURE,
        "max_tokens": config.MAX_TOKENS,
    }

    print(f"\n[HTTP LLM Request] Sending request to {url}")
    print(f"  Model: {config.MODEL}")
    print(f"  Temperature: {config.TEMPERATURE}")
    print(f"  Max Tokens: {config.MAX_TOKENS}")
    print(f"  Timeout: {config.TIMEOUT}")
    print(f"  Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=config.TIMEOUT)
        print(f"[HTTP LLM Response] Received status code {response.status_code}")
        response.raise_for_status()
        
        resp_json = response.json()
        content = resp_json["choices"][0]["message"]["content"]
        print(f"  Choices/Message/Content:\n{content}")
        return str(content).strip()
    except Exception as e:
        print(f"[HTTP LLM Error] Request failed: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"  Response Body: {response.text}")
        traceback.print_exc()
        raise

