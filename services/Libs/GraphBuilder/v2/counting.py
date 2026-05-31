from __future__ import annotations

from collections import Counter

from services.Libs.GraphBuilder.v1.config import CountingConfig


def _count_pairs(
	sentences: list[list[str]],
	config: CountingConfig,
) -> Counter[tuple[str, str]]:
	"""Slide a window over token sequences and accumulate pair weights."""
	counts: Counter[tuple[str, str]] = Counter()

	if config.cross_sentence:
		sequences: list[list[str]] = [[token for sentence in sentences for token in sentence]]
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

