import requests

from Config import config


def init_llm() -> dict:
    """
    Initialize and verify connection to the LLM server.
    Returns details of the configuration being used.
    """
    if config.PROVIDER == "google":
        return {
            "provider": config.PROVIDER,
            "model": config.MODEL,
            "base_url": config.BASE_URL,
        }

    url = (
        f"{config.BASE_URL}/models"
        if config.BASE_URL
        else "http://localhost:11434/v1/models"
    )
    headers = {}
    if config.API_KEY:
        headers["Authorization"] = f"Bearer {config.API_KEY}"

    try:
        response = requests.get(url, headers=headers, timeout=5.0)
        response.raise_for_status()
    except Exception as exc:
        raise ConnectionError(
            f"Could not connect to Ollama/LLM server at {config.BASE_URL or 'localhost:11434'}. "
            f"Please ensure Ollama is running. Error: {exc}"
        ) from exc

    return {
        "provider": config.PROVIDER,
        "model": config.MODEL,
        "base_url": config.BASE_URL,
    }
