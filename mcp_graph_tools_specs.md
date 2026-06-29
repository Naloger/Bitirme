# Model Context Protocol (MCP) — Graph Database Tools Specification

This document lists and details the Model Context Protocol (MCP) tools designed to interface with the graph database (RDF Quadstore). These tools will be implemented on a separate backend server and accessed by the loop agent subgraph via MCP JSON-RPC connection.

---

## 1. Connection Configurations

The MCP client connects to the backend host using the configuration defined in `Config/config.json`. The sample configuration is as follows:

```json
{
  "llm_config": {
    "provider": "ollama",
    "model": "gemma4:e2b",
    "api_key": null,
    "base_url": "http://localhost:11434/v1",
    "temperature": 0.0,
    "max_tokens": 8000,
    "max_loops": 7,
    "timeout": 120.0
  },
  "mcp_config": {
    "enabled": false,
    "server_url": "http://localhost:8000",
    "server_type": "json-rpc",
    "timeout": 15.0,
    "headers": {
      "Authorization": "Bearer sample_token_to_replace"
    }
  }
}
```

---

## 2. Tools Specification

### A. Graph Ingestion & Write Tools

#### 1. `tool_ingest_internal_stream`
* **MCP Name**: `graph_ingest_internal_stream`
* **Description**: Recalls internal RDF statements/quads from a specific named graph context.
* **Arguments**:
  * `source` (string, default: `"knowledge_graph"`): The named graph URI to query.
* **Response**:
  * Array of RDF Quad dicts: `[{"subject": string, "predicate": string, "object": string, "graph": string}]`
* **Graph Operation**: Executes a SPARQL query matching triples within the specified named graph:
  ```sparql
  SELECT ?s ?p ?o ?g WHERE { GRAPH <source_uri> { ?s ?p ?o } } LIMIT 100
  ```

#### 2. `tool_ingest_external_api`
* **MCP Name**: `graph_ingest_external_api`
* **Description**: Simulates or reads parsed external raw incoming text context to turn into proposed quads.
* **Arguments**:
  * `endpoint` (string, default: `"llm_input"`): The target endpoint/graph URI.
* **Response**:
  * Array of RDF Quad dicts.

#### 3. `tool_write_to_quadstore`
* **MCP Name**: `graph_write_to_quadstore`
* **Description**: Inserts a batch of RDF quads atomically into the triplestore/quadstore.
* **Arguments**:
  * `quads` (array of objects): List of quads containing `subject`, `predicate`, `object`, and `graph`.
* **Response**:
  * `success` (boolean): `true` if write succeeded, `false` otherwise.
* **Graph Operation**: Executes a SPARQL INSERT DATA operation:
  ```sparql
  INSERT DATA {
    GRAPH <graph_uri> {
      <subject> <predicate> <object> .
    }
  }
  ```

---

### B. Graph Analytics & Ontology Tools

#### 4. `tool_run_community_detection`
* **MCP Name**: `graph_run_community_detection`
* **Description**: Groups related subjects into communities (GraphRAG-style) based on shared linkage in the quadstore.
* **Arguments**:
  * `quads` (array of objects): The list of RDF quads to analyze.
* **Response**:
  * Array of community clusters: `[{"community_id": string, "members": [string]}]`

#### 5. `tool_map_ontology`
* **MCP Name**: `graph_map_ontology`
* **Description**: Performs ontology schema mapping (e.g., matching to OWL/RDF schemas) and attaches concept metadata.
* **Arguments**:
  * `quads` (array of objects): Quads to validate.
  * `ontology` (string, default: `"default"`): The ontology URI or identifier.
* **Response**:
  * Array of quads annotated with `mapped_concept`.

#### 6. `tool_index_quads`
* **MCP Name**: `graph_index_quads`
* **Description**: Triggers index updates (vector or keyword indexing) for newly written RDF statements.
* **Arguments**:
  * `quads` (array of objects): Quads to index.
* **Response**:
  * Map of statement keys to indexing metadata.

---

### C. Validation & Inference Tools

#### 7. `tool_validate_quads`
* **MCP Name**: `graph_validate_quads`
* **Description**: Applies SHACL constraints or custom rules to detect logical conflicts or invalid relations in the quadstore.
* **Arguments**:
  * `quads` (array of objects): Quads to validate.
* **Response**:
  * Array of issues: `[{"type": string, "quad": string}]`

#### 8. `tool_detect_anomalies`
* **MCP Name**: `graph_detect_anomalies`
* **Description**: Runs Graph Neural Network (GNN) or path-based anomaly detection to find anomalous nodes/cycles.
* **Arguments**:
  * `quads` (array of objects): Quads to analyze.
* **Response**:
  * Array of anomalous node names: `[string]`

#### 9. `tool_infer_missing_quads`
* **MCP Name**: `graph_infer_missing_quads`
* **Description**: Uses deductive inference to generate missing/implied relationship quads.
* **Arguments**:
  * `quads` (array of objects): Currently active quads.
  * `issues` (array of objects): Detected conflicts to avoid during inference.
* **Response**:
  * Array of newly inferred RDF quads.

---

### D. Traversal & Decision Tools

#### 10. `tool_quadstore_traversal`
* **MCP Name**: `graph_quadstore_traversal`
* **Description**: Performs SPARQL traversal to find top-N high centrality/priority nodes.
* **Arguments**:
  * `quads` (array of objects): Graph database quads.
  * `top_n` (integer, default: 3): Number of nodes to retrieve.
* **Response**:
  * Array of node objects: `[{"id": string}]`

#### 11. `tool_quadstore_impact_analysis`
* **MCP Name**: `graph_quadstore_impact_analysis`
* **Description**: Analyzes propagation impact starting from priority nodes to see what other elements are affected.
* **Arguments**:
  * `priority_nodes` (array of objects): Nodes to propagate from.
  * `quads` (array of objects): Graph quads context.
* **Response**:
  * Object containing affected entities list: `{"affected_entities": [string]}`

#### 12. `tool_dispatch_action`
* **MCP Name**: `graph_dispatch_action`
* **Description**: Dispatches the final integrated action via REST/gRPC.
* **Arguments**:
  * `action` (object): Mapped action metadata containing `type`, `target`, and `concept`.
* **Response**:
  * `success` (boolean): `true` if dispatch succeeded.
