# System Design Document: Hybrid Epistemic Agent (HEA)

**Version:** 1.0

**Author:** AI Engineering Collaborator

**Status:** Architecture Blueprint

---

## 1. Executive Summary & Core Intent

The **Hybrid Epistemic Agent (HEA)** is an automated system designed to ingest high-velocity, continuous text streams without suffering from cognitive overload or infinite data duplication. Its core goal is **Meaning Making**—converting unstructured, noisy data streams into an evolving, structured network of interconnected "Wiki Pages" (Knowledge Graph representation).

Instead of relying solely on expensive and slow LLM processing, this architecture uses a **two-tier hybrid engine**:

1. **The Non-LLM Layer (The Sieve):** A deterministic, hardware-efficient processing pipeline that computes lexical entropy and discards redundant inputs (noise).
2. **The LLM Layer (The Architect):** A semantic synthesis engine triggered *only* when the Sieve detects high information gain ($IG$). It parses relationships, bridges multiple wiki pages, and manages states.

---

## 2. Architecture Overview

The system acts as an algorithmic filter based on Information Theory, specifically using the principles of **Information Gain** and **Noisy Channel Coding**.

### The Data Processing Pipeline

1. **Streaming Ingestion:** Raw text enters the system.
2. **Concept Routing (Non-LLM):** Fast keyword/token scanning determines which active Wiki registers the text touches. Unmatched data is instantly dropped.
3. **Lexical Entropy Filter (Non-LLM):** The system calculates the ratio of *novel words* in the incoming text relative to the existing Wiki page state using set theory.
4. **Semantic Extraction (LLM):** If the lexical gain crosses a threshold (e.g., $>15\%$), the text is handed over to a structured LLM call.
5. **Git-like Commit (Multi-Wiki Update):** The LLM isolates the "Content Delta," patches the primary wiki page, creates cross-links to related topics, and logs the change like a Git commit.

---

## 3. Detailed Component Breakdown

### 3.1 The Entropy Sieve & Set-Theory Router

To prevent the agent from processing the same information repeatedly, we model the system's baseline knowledge as a set of unique tokens ($W_{wiki}$). The incoming text stream is broken down into a set of tokens ($W_{input}$).

The mathematical evaluation for **Lexical Information Gain ($IG_{lexical}$)** is:

$$IG_{lexical} = \frac{| W_{input} \setminus W_{wiki} |}{| W_{input} |}$$

If $IG_{lexical} < \theta$ (Threshold), the input contains mostly duplicate concepts and vocabulary, rendering it "low entropy/predictable." It is discarded before any LLM processing occurs.

### 3.2 The Cross-Wiki Coordinator & Graph Topology

When high entropy is caught, the LLM treats individual concepts as separate nodes. Instead of rewriting an entire database, it issues structured data patches using **Pydantic** validation:

* **Primary Updates:** Clean, factual statements appended chronologically to the primary topic node.
* **Bi-directional Cross-Links:** Generates a relational edge linking the current page to another active concept page.
* **State Updates / Deltas:** Uses event-sourcing style mutations, preserving the history of how a concept evolved (analogous to `git diff` histories).

---

## 4. Technical Blueprint (Python Implementation)

Below is the complete, self-contained hybrid architecture utilizing Python, native set functions, and structured LLM outputs.

```python
import re
import time
from typing import List, Dict, Set
from pydantic import BaseModel, Field
from openai import OpenAI

# ----------------------------------------------------
# 1. DATA STRUCTURES & SCHEMAS
# ----------------------------------------------------

class CrossWikiUpdate(BaseModel):
    primary_topic_updates: List[str] = Field(
        description="Purely novel facts belonging strictly to the primary wiki topic being processed."
    )
    related_concept_links: Dict[str, str] = Field(
        description="Mappings to other existing wiki topics. Key: Target Topic, Value: The relationship connecting them."
    )
    contradictions: List[str] = Field(
        description="Factual assertions in the input that directly conflict with data stored in active wiki pages."
    )

# ----------------------------------------------------
# 2. CORE HYBRID CORE ENGINE
# ----------------------------------------------------

class HybridEpistemicAgent:
    def __init__(self, api_key: str):
        self.wikis: Dict[str, str] = {}
        self.concept_router: Dict[str, str] = {}
        self.commit_history: Dict[str, List[str]] = {}
        self.client = OpenAI(api_key=api_key)

    def register_new_concept(self, topic: str, tracking_keywords: List[str]):
        """Seeds a concept track into the ecosystem."""
        self.wikis[topic] = self.wikis.get(topic, "")
        self.commit_history[topic] = self.commit_history.get(topic, [])
        for kw in tracking_keywords:
            self.concept_router[kw.lower()] = topic

    def _tokenize(self, text: str) -> Set[str]:
        return set(re.findall(r'\b\w+\b', text.lower()))

    def calculate_entropy_gain(self, topic: str, text: str) -> float:
        """Non-LLM Layer: Compute vocabulary novelty via set differences."""
        wiki_content = self.wikis.get(topic, "")
        if not wiki_content:
            return 1.0  # Empty wiki means absolute 100% information gain
            
        wiki_tokens = self._tokenize(wiki_content)
        input_tokens = self._tokenize(text)
        
        if not input_tokens:
            return 0.0
            
        novel_tokens = input_tokens - wiki_tokens
        return len(novel_tokens) / len(input_tokens)

    def ingest_stream(self, raw_stream_input: str, entropy_threshold: float = 0.15):
        """High-throughput ingestion pipeline handling routing, filtering, and LLM orchestration."""
        input_tokens = self._tokenize(raw_stream_input)
        
        # Fast Routing Line
        matched_topics = {self.concept_router[kw] for kw in self.concept_router if kw in input_tokens}
        
        if not matched_topics:
            return # Drop immediately: Out of scope

        for topic in matched_topics:
            # S/N Filter Line
            info_gain = self.calculate_entropy_gain(topic, raw_stream_input)
            
            if info_gain < entropy_threshold:
                print(f"[{topic}] Drop Node: Entropy too low ({info_gain:.2%}). Ignored as noise.")
                continue
                
            print(f"[{topic}] High Entropy Detected ({info_gain:.2%}). Orchestrating LLM layer...")
            self._orchestrate_llm_layer(topic, raw_stream_input)

    def _orchestrate_llm_layer(self, primary_topic: str, text: str):
        """LLM Layer: Triggered exclusively for high-value semantic convergence."""
        # Collate context of matched + peripheral wiki records
        context_snapshot = {primary_topic: self.wikis[primary_topic]}
        for t, content in self.wikis.items():
            if t != primary_topic and t.lower() in text.lower():
                context_snapshot[t] = content

        prompt = f"""
        PRIMARY TOPIC: {primary_topic}
        CURRENT ACTIVE KNOWLEDGE CLUSTER:
        {context_snapshot}
        
        NEW INCOMING METADATA STREAM:
        {text}
        """

        completion = self.client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "You are a cross-wiki epistemic compiler. Identify novel data points, track relation links, and catch structural updates."},
                {"role": "user", "content": prompt}
            ],
            response_format=CrossWikiUpdate,
        )
        
        self._commit_deltas(primary_topic, completion.choices[0].message.parsed)

    def _commit_deltas(self, primary_topic: str, delta: CrossWikiUpdate):
        """Git-like commit operation pushing patches to affected nodes."""
        timestamp = time.strftime("%Y-%m-%d %H:%M")
        
        if delta.contradictions:
            print(f"   ⚠️ CONTRADICTION CAUGHT: {delta.contradictions}")
            
        if delta.primary_topic_updates:
            patch_string = " ".join(delta.primary_topic_updates)
            self.wikis[primary_topic] += f"\n- [{timestamp} COMMIT]: {patch_string}"
            self.commit_history[primary_topic].append(f"[{timestamp}] Delta: {patch_string}")
            print(f"   ✅ Patched [{primary_topic}] Wiki node.")
            
        for related_topic, relation in delta.related_concept_links.items():
            if related_topic in self.wikis:
                self.wikis[related_topic] += f"\n- [{timestamp} CROSSLINK FROM {primary_topic}]: {relation}"
                print(f"   🔗 Established edge -> [{related_topic}]")

```

---

## 5. Recommended Learning Resources & Concepts

To deepen your understanding of the math and systemic frameworks supporting this architecture, you should study **Information Theory**, **Vector Databases/Embeddings**, and **Graph RAG**.

### Recommended YouTube Search Journeys

Since specific video URLs fluctuate over time, look up these targeted topics and channels for high-signal instruction:

* **"Information Entropy - 3Blue1Brown"**: The gold standard video for visually understanding Shannon Entropy, bits of information, and surprise values mathematically.
* **"GraphRAG: Microsoft Research Deep Dive"**: Search for Microsoft Research's official presentations or code walkthroughs on *GraphRAG*. This will show you how big tech implements the exact "global wiki-style summaries over graphs" concept you introduced.
* **"Vector Databases & Cosine Similarity Explained Simply"**: Look for video breakdowns by channels like *StatQuest with Josh Starmer* or *ArjanCodes* to understand how embeddings map into multi-dimensional memory maps for quick noise-filtering.
* **"LangChain or LlamaIndex Property Graphs"**: Search for recent tutorials showcasing how these frameworks build dynamic, evolving node networks using native Pydantic wrappers.

### Next-Step Architectural Considerations

As this system runs perpetually, your Wiki nodes will continuously expand. To prevent them from becoming too large for the LLM's context window over time, you will eventually need to introduce an **Aggregation Agent**. This sub-agent can periodically run in the background to clean up old commit histories, merge redundant updates into cohesive paragraphs, and prune weak edges with low verification scores.