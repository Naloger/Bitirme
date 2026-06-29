import requests
from services.Config import config

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

    response = requests.post(url, json=payload, headers=headers, timeout=config.TIMEOUT)
    response.raise_for_status()

    return str(response.json()["choices"][0]["message"]["content"]).strip()
