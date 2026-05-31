from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from services.Libs.GraphBuilder.v1.config import CountingConfig, TokenizerConfig
from services.Libs.GraphBuilder.v2.counting import _count_pairs as _count_pairs_impl
from services.Libs.GraphBuilder.v2.models import CoOccurrenceEdge, ResourceGraph
from services.Libs.GraphBuilder.v2.pipeline import (
	build_resource_graph as _build_resource_graph_impl,
)
from services.Libs.GraphBuilder.v2.pipeline import (
	collect_cooccurrence_edges as _collect_cooccurrence_edges_impl,
)
from services.Libs.GraphBuilder.v2.pipeline import (
	collect_cooccurrence_edges_for_texts as _collect_cooccurrence_edges_for_texts_impl,
)
from services.Libs.Lemmatizer.LanguageSegmentation.segment_by_language import (
	segment_by_language,
)
from services.Libs.Lemmatizer.LemmaNormalization.tokenization import (
	_tokenize_and_lemmatize as _tokenize_and_lemmatize_impl,
)
from services.Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_english import (
	lemmatize as lemmatize_english_text,
)
from services.Libs.Lemmatizer.LemmatizeByLanguage.lemmatize_turkish import (
	lemmatize_turkish_text,
)

__all__ = [
	"TokenizerConfig",
	"CountingConfig",
	"CoOccurrenceEdge",
	"ResourceGraph",
	"lemmatize_text",
	"build_resource_graph",
	"collect_cooccurrence_edges",
	"collect_cooccurrence_edges_for_texts",
]


# ── Compatibility wrappers ────────────────────────────────────────────────────


def _tokenize_and_lemmatize(text: str, config: TokenizerConfig) -> list[list[str]]:
	"""Compatibility wrapper used by the public build pipeline."""
	return _tokenize_and_lemmatize_impl(text, config)


def _count_pairs(sentences: list[list[str]], config: CountingConfig):
	"""Compatibility wrapper used by the public build pipeline."""
	return _count_pairs_impl(sentences, config)


def lemmatize_text(text: str) -> list[str]:
	"""Return language-aware lemmatized lines for mixed English/Turkish text."""
	lines: list[str] = []
	for segment in segment_by_language(text):
		segment_text = segment["text"]
		if segment["language"] == "tr":
			lines.extend(lemmatize_turkish_text(segment_text))
		else:
			lines.extend(lemmatize_english_text(segment_text))
	return lines


# ── Public API ─────────────────────────────────────────────────────────────────


def build_resource_graph(
	text: str,
	*,
	tokenizer_config: TokenizerConfig | None = None,
	counting_config: CountingConfig | None = None,
	resource_node: UUID | None = None,
) -> ResourceGraph:
	"""Full pipeline: tokenize → lemmatize → count → build graph."""
	return _build_resource_graph_impl(
		text,
		tokenizer_config=tokenizer_config,
		counting_config=counting_config,
		resource_node=resource_node,
		tokenize_fn=_tokenize_and_lemmatize,
		count_fn=_count_pairs,
	)


def collect_cooccurrence_edges(
	text: str,
	*,
	tokenizer_config: TokenizerConfig | None = None,
	counting_config: CountingConfig | None = None,
	resource_node: UUID | None = None,
) -> list[CoOccurrenceEdge]:
	"""Convenience wrapper returning only the edge list for a single text."""
	return _collect_cooccurrence_edges_impl(
		text,
		tokenizer_config=tokenizer_config,
		counting_config=counting_config,
		resource_node=resource_node,
		tokenize_fn=_tokenize_and_lemmatize,
		count_fn=_count_pairs,
	)


def collect_cooccurrence_edges_for_texts(
	texts: Sequence[str],
	*,
	tokenizer_config: TokenizerConfig | None = None,
	counting_config: CountingConfig | None = None,
) -> list[CoOccurrenceEdge]:
	"""Process multiple texts and return one flat edge list."""
	return _collect_cooccurrence_edges_for_texts_impl(
		texts,
		tokenizer_config=tokenizer_config,
		counting_config=counting_config,
		tokenize_fn=_tokenize_and_lemmatize,
		count_fn=_count_pairs,
	)


# ── Demo ───────────────────────────────────────────────────────────────────────


def main() -> None:
	sample = (
		"The cats are chasing the mice. "
		"The mice are running away from the cats. "
		"Chasing and running define their relationship."
		"Elma yemek ister misin?"
	)

	graph = build_resource_graph(
		sample,
		tokenizer_config=TokenizerConfig(
			use_stopwords=True,
			pos_filter={"NN", "VB"},
			min_token_length=3,
		),
		counting_config=CountingConfig(
			window_size=1,
			directed=True,
			distance_weighted=True,
			min_edge_weight=0.3,
			cross_sentence=False,
		),
	)

	print(graph.model_dump_json(indent=2))


if __name__ == "__main__":
	main()
