# -*- coding: utf-8 -*-
"""Tests for the Collector Agent graph builder."""
import sys
from pathlib import Path
from uuid import UUID

# Add the inner services package root to path so direct script execution works.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.Libs.GraphBuilder.v1 import collector_agent
from services.Tests.test_helpers import trace_call


def _patch_tokenizer(fake):
    # noinspection PyProtectedMember
    original = collector_agent._tokenize_and_lemmatize
    collector_agent._tokenize_and_lemmatize = fake
    return original


def _patch_module_attr(name: str, fake):
    original = getattr(collector_agent, name)
    setattr(collector_agent, name, fake)
    return original


def test_build_resource_graph_counts_weights():
    """Repeated co-occurrences should accumulate into a single weighted edge."""
    original = _patch_tokenizer(
        lambda text, config: [["apple", "banana", "apple"], ["banana", "apple"]]
    )
    try:
        graph = trace_call(
            collector_agent.build_resource_graph,
            "ignored",
            counting_config=collector_agent.CountingConfig(window_size=1),
        )
        if not isinstance(graph.resource_node, UUID):
            raise AssertionError("Expected a UUID resource node")
        if len(graph.edges) != 1:
            raise AssertionError(f"Expected 1 edge, got {len(graph.edges)}")

        edge = graph.edges[0]
        if edge.resource_node != graph.resource_node:
            raise AssertionError("Edge resource_node should match graph resource_node")
        if (edge.source, edge.target) != ("apple", "banana"):
            raise AssertionError(f"Unexpected edge pair: {(edge.source, edge.target)}")
        if edge.weight != 3:
            raise AssertionError(f"Expected weight 3, got {edge.weight}")
    finally:
        collector_agent._tokenize_and_lemmatize = original


def test_collect_multiple_texts_use_distinct_resource_nodes():
    """Each text input should be assigned its own resource node UUID."""

    def fake_tokenize(text: str, _config):
        if text == "first":
            return [["alpha", "beta"]]
        if text == "second":
            return [["gamma", "delta"]]
        return []

    original = _patch_tokenizer(fake_tokenize)
    try:
        edges = trace_call(
            collector_agent.collect_cooccurrence_edges_for_texts,
            ["first", "second"],
            counting_config=collector_agent.CountingConfig(window_size=1),
        )
        if len(edges) != 2:
            raise AssertionError(f"Expected 2 edges, got {len(edges)}")

        resource_nodes = {edge.resource_node for edge in edges}
        if len(resource_nodes) != 2:
            raise AssertionError("Expected one UUID per processed text")
    finally:
        collector_agent._tokenize_and_lemmatize = original


def test_empty_text_returns_empty_edges():
    """Empty input should still produce a UUID-backed graph with no edges."""
    original = _patch_tokenizer(lambda text, config: [])
    try:
        graph = trace_call(
            collector_agent.build_resource_graph,
            "",
            counting_config=collector_agent.CountingConfig(window_size=1),
        )
        if not isinstance(graph.resource_node, UUID):
            raise AssertionError("Expected a UUID resource node")
        if graph.edges:
            raise AssertionError(f"Expected no edges, got {graph.edges}")
        if graph.lemmatized_tokens:
            raise AssertionError(f"Expected no tokens, got {graph.lemmatized_tokens}")
    finally:
        collector_agent._tokenize_and_lemmatize = original


def test_lemmatize_text_uses_language_segments():
    """Mixed-language text should be segmented before lemmatization."""
    original_segment = _patch_module_attr(
        "segment_by_language",
        lambda text: [
            {"language": "en", "text": "Hello world."},
            {"language": "tr", "text": "Merhaba dünya."},
        ],
    )
    original_en = _patch_module_attr(
        "lemmatize_english_text",
        lambda text: ["hello world"],
    )
    original_tr = _patch_module_attr(
        "lemmatize_turkish_text",
        lambda text: ["merhaba dunya"],
    )
    try:
        result = trace_call(collector_agent.lemmatize_text, "Hello world. Merhaba dünya.")
        expected = ["hello world", "merhaba dunya"]
        if result != expected:
            raise AssertionError(f"Expected segmented lemmatization {expected}, got {result}")
    finally:
        collector_agent.segment_by_language = original_segment
        collector_agent.lemmatize_english_text = original_en
        collector_agent.lemmatize_turkish_text = original_tr


if __name__ == "__main__":
    test_build_resource_graph_counts_weights()
    test_collect_multiple_texts_use_distinct_resource_nodes()
    test_empty_text_returns_empty_edges()
    test_lemmatize_text_uses_language_segments()
    print("\n✓ All collector tests passed!")
