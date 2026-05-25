# Collector Agent

Pydantic-based text collector that:

1. Lemmatizes input text with `services.Libs.Lemmatizer.lemmatize_text`.
2. Normalizes the lemmatized tokens.
3. Builds a weighted co-occurrence graph.
4. Assigns one UUID `resource_node` per processed text input.

## Main API

- `build_resource_graph(text, window_size=2, resource_node=None) -> ResourceGraph`
- `collect_cooccurrence_edges(text, window_size=2, resource_node=None) -> list[CoOccurrenceEdge]`
- `collect_cooccurrence_edges_for_texts(texts, window_size=2) -> list[CoOccurrenceEdge]`

## Example

```python
from services.Agents.CollectorAgent.collector_agent import build_resource_graph

graph = build_resource_graph("The cats are running. The cats are sleeping.")
print(graph.resource_node)
print(graph.edges)
```

