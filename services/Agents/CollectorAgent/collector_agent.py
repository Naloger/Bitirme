from __future__ import annotations

from collections import Counter
from typing import Sequence
from uuid import UUID, uuid4

import nltk
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import sent_tokenize, word_tokenize
from pydantic import BaseModel, Field
from services.Libs.Lemmatizer.lemmatize_english import lemmatize_english_text
from services.Libs.Lemmatizer.lemmatize_turkish import lemmatize_turkish_text
from services.Libs.Lemmatizer.segment_by_language import segment_by_language

# ── NLTK bootstrap ────────────────────────────────────────────────────────────

_lemmatizer = WordNetLemmatizer()
_nltk_ready = False


def _ensure_nltk_data() -> None:
	global _nltk_ready
	if _nltk_ready:
		return
	for resource, path in [
		("punkt_tab",                       "tokenizers/punkt_tab"),
		("stopwords",                        "corpora/stopwords"),
		("wordnet",                          "corpora/wordnet"),
		("averaged_perceptron_tagger_eng",   "taggers/averaged_perceptron_tagger_eng"),
	]:
		try:
			nltk.data.find(path)
		except LookupError:
			nltk.download(resource, quiet=True)
	_nltk_ready = True


def _penn_to_wordnet(tag: str) -> str:
	"""Map a Penn Treebank POS tag to a WordNet POS constant."""
	if tag.startswith("J"):
		return wordnet.ADJ
	if tag.startswith("V"):
		return wordnet.VERB
	if tag.startswith("R"):
		return wordnet.ADV
	return wordnet.NOUN  # default — covers NN, NNS, NNP, …


def _nltk_language_name(language_code: str) -> str:
	"""Map a short language code to the NLTK language name used by tokenizers."""
	return {"en": "english", "tr": "turkish"}.get(language_code, language_code)


def _build_stop_set(config: "TokenizerConfig", language_code: str) -> set[str]:
	"""Build a normalized stopword set for one segment language."""
	stop_set: set[str] = set()
	if config.use_stopwords:
		try:
			stop_set = set(stopwords.words(_nltk_language_name(language_code)))
		except LookupError:
			stop_set = set()
	stop_set |= {w.lower() for w in config.extra_stopwords}
	return stop_set


def _normalize_tokens(
	tokens: list[str],
	*,
	config: "TokenizerConfig",
	stop_set: set[str],
) -> list[str]:
	"""Apply common token filters after language-specific lemmatization."""
	normalized: list[str] = []
	for token in tokens:
		cleaned = token.lower() if config.lowercase else token
		cleaned = cleaned.strip()
		if not cleaned:
			continue
		if not cleaned.isalpha():
			continue
		if len(cleaned) < config.min_token_length:
			continue
		if cleaned in stop_set:
			continue
		normalized.append(cleaned)
	return normalized


def _tokenize_english_segment(text: str, config: "TokenizerConfig") -> list[list[str]]:
	"""Tokenize and lemmatize one English segment."""
	_ensure_nltk_data()
	stop_set = _build_stop_set(config, "en")
	result: list[list[str]] = []

	if config.pos_filter is None:
		for line in lemmatize_english_text(text):
			tokens = _normalize_tokens(line.split(), config=config, stop_set=stop_set)
			if tokens:
				result.append(tokens)
		return result

	for sentence in sent_tokenize(text, language="english"):
		raw_tokens = word_tokenize(sentence, language="english")
		tagged: list[tuple[str, str]] = nltk.pos_tag(raw_tokens)

		tokens: list[str] = []
		for word, tag in tagged:
			if config.lowercase:
				word = word.lower()

			if not word.isalpha():
				continue
			if len(word) < config.min_token_length:
				continue
			if word in stop_set:
				continue
			if config.pos_filter is not None and not any(
				tag.startswith(prefix) for prefix in config.pos_filter
			):
				continue

			lemma = _lemmatizer.lemmatize(word, _penn_to_wordnet(tag))
			tokens.append(lemma)

		if tokens:
			result.append(tokens)

	return result


def _tokenize_turkish_segment(text: str, config: "TokenizerConfig") -> list[list[str]]:
	"""Tokenize and lemmatize one Turkish segment."""
	stop_set = _build_stop_set(config, "tr")
	result: list[list[str]] = []

	for line in lemmatize_turkish_text(text):
		tokens = _normalize_tokens(line.split(), config=config, stop_set=stop_set)
		if tokens:
			result.append(tokens)

	return result


# ── Configuration models ───────────────────────────────────────────────────────

class TokenizerConfig(BaseModel):
	"""Controls how raw text is converted into lemmatized tokens."""

	language: str = Field(
		default="english",
		description=(
			"Fallback language hint used by the legacy English tokenizer path; mixed text "
			"is segmented by detected language before lemmatization."
		),
	)
	use_stopwords: bool = Field(
		default=True,
		description="Remove NLTK stopwords for the chosen language.",
	)
	extra_stopwords: set[str] = Field(
		default_factory=set,
		description="Additional tokens to discard after lowercasing.",
	)
	pos_filter: set[str] | None = Field(
		default=None,
		description=(
			"If set, only tokens whose Penn Treebank tag *starts with* one of these "
			"prefixes are kept on the English POS-aware path. Example: {'NN', 'VB'} "
			"keeps nouns and verbs only. None keeps every POS."
		),
	)
	min_token_length: int = Field(
		default=2,
		ge=1,
		description="Discard tokens shorter than this after lowercasing.",
	)
	lowercase: bool = Field(
		default=True,
		description="Lowercase every token before filtering and lemmatizing.",
	)


class CountingConfig(BaseModel):
	"""Controls how co-occurrence pairs are counted and which edges survive."""

	window_size: int = Field(
		default=2,
		ge=1,
		description="Maximum distance (in tokens) between source and target to form a pair.",
	)
	directed: bool = Field(
		default=False,
		description=(
			"When False (default) edges are undirected: (a, b) and (b, a) are merged "
			"into one canonical pair sorted alphabetically.  When True, order is preserved."
		),
	)
	distance_weighted: bool = Field(
		default=False,
		description=(
			"When True, each co-occurrence increments the edge weight by 1 / distance "
			"instead of 1, so adjacent pairs contribute more than distant ones."
		),
	)
	min_edge_weight: float = Field(
		default=1.0,
		ge=0.0,
		description="Edges whose accumulated weight is below this threshold are pruned.",
	)
	cross_sentence: bool = Field(
		default=False,
		description=(
			"When False (default) the window never crosses a sentence boundary. "
			"When True the entire text is treated as a single token sequence."
		),
	)


# ── Domain models ─────────────────────────────────────────────────────────────

class CoOccurrenceEdge(BaseModel):
	"""A weighted co-occurrence edge produced from a single text resource."""

	resource_node: UUID = Field(description="UUID assigned to the processed text input.")
	source: str = Field(min_length=1, description="Source token for the edge.")
	target: str = Field(min_length=1, description="Target token for the edge.")
	weight: float = Field(ge=0.0, description="Accumulated co-occurrence score.")


class ResourceGraph(BaseModel):
	"""Container for one processed text input and its co-occurrence graph."""

	# resource_node: UUID = Field(default_factory=uuid4, description="UUID for this text input.")
	# source_text: str = Field(default="", description="Original text that was processed.")
	# lemmatized_tokens: list[str] = Field(
	# 	default_factory=list,
	# 	description="Flat list of normalized tokens used to build the graph.",
	# )
	edges: list[CoOccurrenceEdge] = Field(
		default_factory=list,
		description="Weighted co-occurrence edges, sorted by descending weight.",
	)
	# tokenizer_config: TokenizerConfig = Field(default_factory=TokenizerConfig)
	# counting_config: CountingConfig = Field(default_factory=CountingConfig)


# ── Tokenization pipeline ──────────────────────────────────────────────────────

def _tokenize_and_lemmatize(
	text: str,
	config: TokenizerConfig,
) -> list[list[str]]:
	"""Return one token list per language-aware segment after lemmatization."""
	result: list[list[str]] = []

	for segment in segment_by_language(text):
		segment_text = segment["text"]
		language = segment["language"]
		if language == "tr":
			result.extend(_tokenize_turkish_segment(segment_text, config))
		else:
			result.extend(_tokenize_english_segment(segment_text, config))

	return result


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


# ── Counting pipeline ──────────────────────────────────────────────────────────

def _count_pairs(
	sentences: list[list[str]],
	config: CountingConfig,
) -> Counter[tuple[str, str]]:
	"""Slide a window over token sequences and accumulate pair weights."""
	counts: Counter[tuple[str, str]] = Counter()

	# Honour (or ignore) sentence boundaries.
	sequences: list[list[str]]
	if config.cross_sentence:
		sequences = [[token for sentence in sentences for token in sentence]]
	else:
		sequences = sentences

	for tokens in sequences:
		for i, source in enumerate(tokens):
			upper = min(len(tokens), i + config.window_size + 1)
			for j in range(i + 1, upper):
				target = tokens[j]
				if source == target:
					continue

				distance = j - i
				increment: float = (1.0 / distance) if config.distance_weighted else 1.0

				if config.directed:
					counts[(source, target)] += increment
				else:
					left, right = sorted((source, target))
					counts[(left, right)] += increment

	return counts


# ── Public API ─────────────────────────────────────────────────────────────────

def build_resource_graph(
	text: str,
	*,
	tokenizer_config: TokenizerConfig | None = None,
	counting_config: CountingConfig | None = None,
	resource_node: UUID | None = None,
) -> ResourceGraph:
	"""Full pipeline: tokenize → lemmatize → count → build graph."""
	tok_cfg = tokenizer_config or TokenizerConfig()
	cnt_cfg = counting_config or CountingConfig()
	resource_id = resource_node or uuid4()

	sentences = _tokenize_and_lemmatize(text, tok_cfg)
	pair_counts = _count_pairs(sentences, cnt_cfg)

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
		# resource_node=resource_id,
		# source_text=text,
		# lemmatized_tokens=[token for sentence in sentences for token in sentence],
		edges=edges,
		# tokenizer_config=tok_cfg,
		# counting_config=cnt_cfg,
	)


def collect_cooccurrence_edges(
	text: str,
	*,
	tokenizer_config: TokenizerConfig | None = None,
	counting_config: CountingConfig | None = None,
	resource_node: UUID | None = None,
) -> list[CoOccurrenceEdge]:
	"""Convenience wrapper returning only the edge list for a single text."""
	return build_resource_graph(
		text,
		tokenizer_config=tokenizer_config,
		counting_config=counting_config,
		resource_node=resource_node,
	).edges


def collect_cooccurrence_edges_for_texts(
	texts: Sequence[str],
	*,
	tokenizer_config: TokenizerConfig | None = None,
	counting_config: CountingConfig | None = None,
) -> list[CoOccurrenceEdge]:
	"""Process multiple texts and return one flat edge list."""
	edges: list[CoOccurrenceEdge] = []
	for text in texts:
		edges.extend(
			collect_cooccurrence_edges(
				text,
				tokenizer_config=tokenizer_config,
				counting_config=counting_config,
			)
		)
	return edges


# ── Demo ───────────────────────────────────────────────────────────────────────

def main() -> None:
	sample = (
		"The cats are chasing the mice. "
		"The mice are running away from the cats. "
		"Chasing and running define their relationship."
	)

	# Nouns + verbs only, distance-weighted, directed, no cross-sentence pairs.
	graph = build_resource_graph(
		sample,
		tokenizer_config=TokenizerConfig(
			use_stopwords=True,
			pos_filter={"NN", "VB"},          # nouns and verbs only
			min_token_length=3,
		),
		counting_config=CountingConfig(
			window_size=1,
			directed=True,
			distance_weighted=True,            # adjacent pairs score higher
			min_edge_weight=0.3,               # prune very weak links
			cross_sentence=False,              # respect sentence boundaries
		),
	)

	print(graph.model_dump_json(indent=2))


if __name__ == "__main__":
	main()

