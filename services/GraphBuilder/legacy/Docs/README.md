# GraphBuilder modules

This package is split into reusable pieces:

- `collector_agent.py` — backward-compatible facade for the original co-occurrence graph API.
- `config.py` — shared `TokenizerConfig` and `CountingConfig` models.
- `models.py` — `CoOccurrenceEdge` and `ResourceGraph` domain models.
- `tokenization.py` — language-aware tokenization and lemmatization helpers.
- `counting.py` — token-pair counting logic.
- `pipeline.py` — reusable graph-building pipeline functions.
- `shared_normalization.py` — reusable text cleaning, co-occurrence, PPMI, and payload helpers.
- `api_models.py` — shared Pydantic API record/payload models.
- `collector_agent_3.py` — legacy `TextNormalizer` using the shared normalization helpers.
- `collector_agent_4.py` — spaCy/httpx `TextNormalizer` using the shared normalization helpers.

## Quick usage

```python
from services.GraphBuilder import build_resource_graph, TokenizerConfig, CountingConfig

graph = build_resource_graph(
    "Hello world",
    tokenizer_config=TokenizerConfig(min_token_length=2),
    counting_config=CountingConfig(window_size=2),
)
```

