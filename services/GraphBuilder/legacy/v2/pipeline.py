from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from uuid import UUID, uuid4

from services.GraphBuilder.legacy.v1.config import CountingConfig, TokenizerConfig
from services.GraphBuilder.legacy.v2.counting import (
	_count_pairs as _count_pairs_default,
)
from services.GraphBuilder.legacy.v2.models import CoOccurrenceEdge, ResourceGraph
from services.Libs.Lemmatizer.LemmaNormalization.tokenization import (
	_tokenize_and_lemmatize as _tokenize_and_lemmatize_default,
)

TokenizeFn = Callable[[str, TokenizerConfig], list[list[str]]]
CountFn = Callable[[list[list[str]], CountingConfig], Counter[tuple[str, str]]]


def build_resource_graph(
	text: str,
	*,
	tokenizer_config: TokenizerConfig | None = None,
	counting_config: CountingConfig | None = None,
	resource_node: UUID | None = None,
	tokenize_fn: TokenizeFn | None = None,
	count_fn: CountFn | None = None,
) -> ResourceGraph:
	"""Full pipeline: tokenize → lemmatize → count → build graph."""
	tok_cfg = tokenizer_config or TokenizerConfig()
	cnt_cfg = counting_config or CountingConfig()
	resource_id = resource_node or uuid4()
	tokenize = tokenize_fn or _tokenize_and_lemmatize_default
	count = count_fn or _count_pairs_default

	sentences = tokenize(text, tok_cfg)
	pair_counts = count(sentences, cnt_cfg)

	edges = [
		CoOccurrenceEdge(
			resource_node=resource_id,
			source=src,
			target=tgt,
			weight=round(weight, 6),
		)
		for (src, tgt), weight in sorted(
			pair_counts.items(),
			key=lambda item: (-item[1], item[0][0], item[0][1]),
		)
		if weight >= cnt_cfg.min_edge_weight
	]

	return ResourceGraph(
		resource_node=resource_id,
		source_text=text,
		lemmatized_tokens=[token for sentence in sentences for token in sentence],
		edges=edges,
		tokenizer_config=tok_cfg,
		counting_config=cnt_cfg,
	)


def collect_cooccurrence_edges(
	text: str,
	*,
	tokenizer_config: TokenizerConfig | None = None,
	counting_config: CountingConfig | None = None,
	resource_node: UUID | None = None,
	tokenize_fn: TokenizeFn | None = None,
	count_fn: CountFn | None = None,
) -> list[CoOccurrenceEdge]:
	"""Convenience wrapper returning only the edge list for a single text."""
	return build_resource_graph(
		text,
		tokenizer_config=tokenizer_config,
		counting_config=counting_config,
		resource_node=resource_node,
		tokenize_fn=tokenize_fn,
		count_fn=count_fn,
	).edges


def collect_cooccurrence_edges_for_texts(
	texts: Sequence[str],
	*,
	tokenizer_config: TokenizerConfig | None = None,
	counting_config: CountingConfig | None = None,
	tokenize_fn: TokenizeFn | None = None,
	count_fn: CountFn | None = None,
) -> list[CoOccurrenceEdge]:
	"""Process multiple texts and return one flat edge list."""
	edges: list[CoOccurrenceEdge] = []
	for text in texts:
		edges.extend(
			collect_cooccurrence_edges(
				text,
				tokenizer_config=tokenizer_config,
				counting_config=counting_config,
				tokenize_fn=tokenize_fn,
				count_fn=count_fn,
			)
		)
	return edges

