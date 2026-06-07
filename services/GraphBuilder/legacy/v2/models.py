from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from services.GraphBuilder.legacy.v1.config import CountingConfig, TokenizerConfig


class CoOccurrenceEdge(BaseModel):
	"""A weighted co-occurrence edge produced from a single text resource."""

	resource_node: UUID = Field(description="UUID assigned to the processed text input.")
	source: str = Field(min_length=1, description="Source token for the edge.")
	target: str = Field(min_length=1, description="Target token for the edge.")
	weight: float = Field(ge=0.0, description="Accumulated co-occurrence score.")


class ResourceGraph(BaseModel):
	"""Container for one processed text input and its co-occurrence graph."""

	resource_node: UUID = Field(default_factory=uuid4, description="UUID for this text input.")
	source_text: str = Field(default="", description="Original text that was processed.")
	lemmatized_tokens: list[str] = Field(
		default_factory=list,
		description="Flat list of normalized tokens used to build the graph.",
	)
	edges: list[CoOccurrenceEdge] = Field(
		default_factory=list,
		description="Weighted co-occurrence edges, sorted by descending weight.",
	)
	tokenizer_config: TokenizerConfig = Field(default_factory=TokenizerConfig)
	counting_config: CountingConfig = Field(default_factory=CountingConfig)

