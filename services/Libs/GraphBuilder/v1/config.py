from __future__ import annotations

from pydantic import BaseModel, Field


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

