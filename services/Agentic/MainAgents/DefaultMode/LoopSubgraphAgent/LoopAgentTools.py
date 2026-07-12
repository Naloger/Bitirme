"""
Cognitive Graph Operating System — LangGraph Implementation
============================================================
Four-node feedback-loop architecture based on the cognitive paradigm design:
  Collector  → Organizer → Reflector → Integrator → (feedback) → Collector/Reflector
"""

from __future__ import annotations
import random
import requests
import subprocess
import json
import threading
import traceback
from Config import config
from services.Agentic.MainAgents.DefaultMode.LoopSubgraphAgent.LoopAgentModels import Quad


# ─────────────────────────────────────────────────────────────────────────────
# MCP Stdio Subprocess Client (Singleton)
# ─────────────────────────────────────────────────────────────────────────────

class MCPStdioClient:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.process = None
        self.initialized = False

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def start(self) -> bool:
        if self.process is not None and self.process.poll() is None:
            return True
        
        try:
            cmd = [config.MCP_COMMAND] + config.MCP_ARGS
            print(f"    [MCP Client] Spawning stdio process: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Start a daemon thread to consume and echo stderr to avoid buffer blockages and aid debugging
            t = threading.Thread(target=self._log_stderr, args=(self.process,), daemon=True)
            t.start()

            # Perform initialize handshake
            init_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "loop-agent-client", "version": "1.0.0"}
                }
            }
            print(f"    [MCP Stdio Handshake] Sending initialization: {json.dumps(init_payload, indent=2)}")
            self._write(init_payload)
            init_response = self._read()
            print(f"    [MCP Stdio Handshake] Received response: {json.dumps(init_response, indent=2)}")
            if not init_response or "result" not in init_response:
                raise RuntimeError(f"Handshake failed. Response: {init_response}")

            # Send initialized notification
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            print(f"    [MCP Stdio Handshake] Sending initialized notification: {json.dumps(initialized_notification)}")
            self._write(initialized_notification)
            
            self.initialized = True
            return True
        except Exception as e:
            print(f"    [MCP Warning] Failed to start MCP process: {e}")
            traceback.print_exc()
            self.close()
            return False

    def _write(self, message: dict):
        if self.process and self.process.stdin:
            line = json.dumps(message)
            self.process.stdin.write(line + "\n")
            self.process.stdin.flush()

    def _read(self) -> dict | None:
        if self.process and self.process.stdout:
            line = self.process.stdout.readline()
            if line:
                return json.loads(line)
        return None

    def _log_stderr(self, proc: subprocess.Popen):
        try:
            for line in iter(proc.stderr.readline, ''):
                if line:
                    print(f"    [MCP Server Log] {line.strip()}")
        except Exception:
            pass

    def call_tool(self, tool_name: str, arguments: dict) -> any:
        if not self.start():
            print(f"    [MCP Stdio] Could not start MCP stdio client for '{tool_name}'.")
            return None
        
        try:
            call_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            print(f"    [MCP Stdio Request] Sending tool call: {json.dumps(call_payload, indent=2)}")
            self._write(call_payload)
            response = self._read()
            print(f"    [MCP Stdio Response] Received tool response: {json.dumps(response, indent=2)}")
            if response and "result" in response:
                content = response["result"].get("content", [])
                if content and isinstance(content, list):
                    text_block = content[0].get("text", "")
                    try:
                        result_val = json.loads(text_block)
                    except json.JSONDecodeError:
                        result_val = text_block
                else:
                    result_val = content
                print(f"    [MCP Stdio] Tool '{tool_name}' call succeeded. Parsed result: {json.dumps(result_val, indent=2)}")
                return result_val
            elif response and "error" in response:
                print(f"    [MCP Warning] Server returned error: {response['error']}")
            return None
        except Exception as e:
            print(f"    [MCP Warning] Tool execution failed: {e}")
            traceback.print_exc()
            return None

    def close(self):
        if self.process:
            try:
                self.process.stdin.close()
            except Exception:
                pass
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                pass
            self.process = None
            self.initialized = False


# ─────────────────────────────────────────────────────────────────────────────
# MCP Client Invocation Helper
# ─────────────────────────────────────────────────────────────────────────────

def _invoke_mcp_tool(tool_name: str, arguments: dict) -> any:
    """Helper to call an MCP tool. Returns None if MCP is disabled or fails, allowing fallback."""
    if not config.MCP_ENABLED:
        print(f"    [MCP Client] MCP is disabled. Using local mock/fallback for '{tool_name}'...")
        return None
    
    print(f"\n    [MCP Client] Invoking MCP tool '{tool_name}' with arguments: {json.dumps(arguments, indent=2)}")
    
    if config.MCP_TRANSPORT == "stdio":
        return MCPStdioClient.get_instance().call_tool(tool_name, arguments)
    
    # SSE / HTTP fallback
    url = f"{config.MCP_SERVER_URL.rstrip('/')}/rpc" if hasattr(config, "MCP_SERVER_URL") else ""
    if not url:
        print(f"    [MCP Client] No MCP server URL configured. Falling back to local for '{tool_name}'...")
        return None

    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": 1
    }
    headers = {
        "Content-Type": "application/json",
        **getattr(config, "MCP_HEADERS", {})
    }
    try:
        print(f"    [MCP Client] Calling {tool_name} on {config.MCP_SERVER_URL} via HTTP...")
        print(f"    [MCP Client] HTTP Request Payload: {json.dumps(payload, indent=2)}")
        response = requests.post(url, json=payload, headers=headers, timeout=config.MCP_TIMEOUT)
        print(f"    [MCP Client] HTTP Response Status Code: {response.status_code}")
        response.raise_for_status()
        res_data = response.json()
        print(f"    [MCP Client] Raw HTTP response content: {json.dumps(res_data, indent=2)}")
        if "error" in res_data:
            print(f"    [MCP Warning] Server returned error: {res_data['error']}")
            return None
        
        content = res_data.get("result", {}).get("content", [])
        if content and isinstance(content, list):
            text_block = content[0].get("text", "")
            try:
                result_val = json.loads(text_block)
            except json.JSONDecodeError:
                result_val = text_block
        else:
            result_val = content
        
        print(f"    [MCP Client] Tool '{tool_name}' call succeeded. Parsed result: {json.dumps(result_val, indent=2)}")
        return result_val
    except Exception as e:
        print(f"    [MCP Warning] SSE/HTTP Connection failed, falling back to local. Error: {e}")
        traceback.print_exc()
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Graph Database Operations (MCP-enabled with local fallback)
# ─────────────────────────────────────────────────────────────────────────────

# ── Collector tools ──────────────────────────────────────────────────────────

def tool_ingest_internal_stream(source: str = "knowledge_graph") -> list[dict]:
    """Simulate recalling internal statements from the knowledge graph."""
    mcp_res = _invoke_mcp_tool("graph_ingest_internal_stream", {"source": source})
    if mcp_res is not None:
        return mcp_res

    print(f"    [tool] ingest_internal_stream(source={source!r})")
    return [
        {"subject": f"stmt_{i}", "predicate": "RECALLED_FROM", "object": "knowledge_graph", "graph": source}
        for i in range(3)
    ]


def tool_ingest_external_api(endpoint: str = "llm_input") -> list[dict]:
    """Simulate ingesting standard LLM input text."""
    mcp_res = _invoke_mcp_tool("graph_ingest_external_api", {"endpoint": endpoint})
    if mcp_res is not None:
        return mcp_res

    print(f"    [tool] ingest_external_api(endpoint={endpoint!r})")
    return [
        {"subject": f"parsed_{i}", "predicate": "EXTRACTED_FROM", "object": "llm_input", "graph": endpoint}
        for i in range(3)
    ]


def tool_write_to_quadstore(
    quads: list[Quad] | list[dict],
    overwrite: bool = False,
    clear_contexts: list[str] | None = None
) -> bool:
    """Simulate atomic RDF quad creation/insertion into a triplestore/quadstore."""
    serialized_quads = [
        q.model_dump() if hasattr(q, "model_dump") else q
        for q in quads
    ]
    mcp_res = _invoke_mcp_tool("graph_write_to_quadstore", {
        "quads": serialized_quads,
        "overwrite": overwrite,
        "clear_contexts": clear_contexts
    })
    if mcp_res is not None:
        return bool(mcp_res.get("success", True) if isinstance(mcp_res, dict) else mcp_res)

    print(f"    [tool] write_to_quadstore({len(quads)} quads)")
    for q in quads:
        subject = q.subject if hasattr(q, "subject") else q.get("subject")
        predicate = q.predicate if hasattr(q, "predicate") else q.get("predicate")
        obj = q.object if hasattr(q, "object") else q.get("object")
        graph = q.graph if hasattr(q, "graph") else q.get("graph")
        print(f"      • Quad: ({subject}, {predicate}, {obj}) inside Graph URI: {graph}")
    return True


# ── Organizer tools ──────────────────────────────────────────────────────────

def tool_run_community_detection(quads: list[Quad] | list[dict]) -> list[dict]:
    """Simulate community/cluster grouping of subjects from atomic quads."""
    serialized_quads = [
        q.model_dump() if hasattr(q, "model_dump") else q
        for q in quads
    ]
    mcp_res = _invoke_mcp_tool("graph_run_community_detection", {"quads": serialized_quads})
    if mcp_res is not None:
        return mcp_res

    print(f"    [tool] run_community_detection(on {len(quads)} quads)")
    subjects = list({q.subject if hasattr(q, "subject") else q.get("subject") for q in quads if q})
    community_ids = list({s[0] for s in subjects if s})
    return [{"community_id": cid, "members": [s for s in subjects if s.startswith(cid)]}
            for cid in community_ids]


def tool_map_ontology(quads: list[Quad] | list[dict], ontology: str = "default") -> list[dict]:
    """Simulate OWL/RDF ontology checking — assign concept metadata to quads."""
    serialized_quads = [
        q.model_dump() if hasattr(q, "model_dump") else q
        for q in quads
    ]
    mcp_res = _invoke_mcp_tool("graph_map_ontology", {"quads": serialized_quads, "ontology": ontology})
    if mcp_res is not None:
        return mcp_res

    print(f"    [tool] map_ontology(ontology={ontology!r})")
    mapped = []
    for q in quads:
        subject = q.subject if hasattr(q, "subject") else q.get("subject")
        predicate = q.predicate if hasattr(q, "predicate") else q.get("predicate")
        obj = q.object if hasattr(q, "object") else q.get("object")
        graph = q.graph if hasattr(q, "graph") else q.get("graph")
        mapped.append({
            "subject": subject, "predicate": predicate, "object": obj, "graph": graph,
            "mapped_concept": "rdf_concept"
        })
    return mapped


def tool_index_quads(quads: list[Quad] | list[dict]) -> dict:
    """Simulate vector or elasticsearch indexing on atomic RDF statements."""
    serialized_quads = [
        q.model_dump() if hasattr(q, "model_dump") else q
        for q in quads
    ]
    mcp_res = _invoke_mcp_tool("graph_index_quads", {"quads": serialized_quads})
    if mcp_res is not None:
        return mcp_res

    print(f"    [tool] index_quads({len(quads)} quads)")
    indexed = {}
    for q in quads:
        subject = q.subject if hasattr(q, "subject") else q.get("subject")
        predicate = q.predicate if hasattr(q, "predicate") else q.get("predicate")
        obj = q.object if hasattr(q, "object") else q.get("object")
        key = f"{subject}-{predicate}-{obj}"
        indexed[key] = {"concept": "indexed_statement"}
    return indexed


# ── Reflector tools ──────────────────────────────────────────────────────────

def tool_validate_quads(quads: list[Quad] | list[dict]) -> list[dict]:
    """Simulate SHACL / constraint-language validation on atomic RDF quads."""
    serialized_quads = [
        q.model_dump() if hasattr(q, "model_dump") else q
        for q in quads
    ]
    mcp_res = _invoke_mcp_tool("graph_validate_quads", {"quads": serialized_quads})
    if mcp_res is not None:
        return mcp_res

    print(f"    [tool] validate_quads()")
    issues = []
    for q in quads:
        subject = q.subject if hasattr(q, "subject") else q.get("subject")
        predicate = q.predicate if hasattr(q, "predicate") else q.get("predicate")
        obj = q.object if hasattr(q, "object") else q.get("object")
        if random.random() < 0.2:
            issues.append({"type": "conflict_quad", "quad": f"({subject}, {predicate}, {obj})"})
    return issues


def tool_detect_anomalies(quads: list[Quad] | list[dict]) -> list[str]:
    """Simulate GNN-based anomaly detection over the RDF quad linkages."""
    serialized_quads = [
        q.model_dump() if hasattr(q, "model_dump") else q
        for q in quads
    ]
    mcp_res = _invoke_mcp_tool("graph_detect_anomalies", {"quads": serialized_quads})
    if mcp_res is not None:
        return mcp_res

    print(f"    [tool] detect_anomalies()")
    subjects = {q.subject if hasattr(q, "subject") else q.get("subject") for q in quads if q}
    return [s for s in subjects if len(s) > 10 and random.random() < 0.15]


def tool_infer_missing_quads(quads: list[Quad] | list[dict], issues: list[dict]) -> list[dict]:
    """Suggest inferred RDF quads based on structured relations."""
    serialized_quads = [
        q.model_dump() if hasattr(q, "model_dump") else q
        for q in quads
    ]
    mcp_res = _invoke_mcp_tool("graph_infer_missing_quads", {"quads": serialized_quads, "issues": issues})
    if mcp_res is not None:
        return mcp_res

    print(f"    [tool] infer_missing_quads()")
    inferred = []
    issue_keys = {iss.get("quad") for iss in issues}
    for q in quads:
        subject = q.subject if hasattr(q, "subject") else q.get("subject")
        predicate = q.predicate if hasattr(q, "predicate") else q.get("predicate")
        obj = q.object if hasattr(q, "object") else q.get("object")
        graph = q.graph if hasattr(q, "graph") else q.get("graph")
        key = f"({subject}, {predicate}, {obj})"
        if key not in issue_keys and random.random() < 0.3:
            inferred.append({
                "subject": obj,
                "predicate": "LOGICALLY_LINKED_TO",
                "object": subject,
                "graph": f"inferred_{graph}"
            })
    return inferred


# ── Integrator tools ─────────────────────────────────────────────────────────

def tool_quadstore_traversal(quads: list[Quad] | list[dict], top_n: int = 3) -> list[dict]:
    """Simulate SPARQL query top-N centrality traversal over quads."""
    serialized_quads = [
        q.model_dump() if hasattr(q, "model_dump") else q
        for q in quads
    ]
    mcp_res = _invoke_mcp_tool("graph_quadstore_traversal", {"quads": serialized_quads, "top_n": top_n})
    if mcp_res is not None:
        return mcp_res

    print(f"    [tool] quadstore_traversal(top_n={top_n})")
    subjects = list({q.subject if hasattr(q, "subject") else q.get("subject") for q in quads if q})
    return [{"id": s} for s in subjects[:top_n]]


def tool_quadstore_impact_analysis(priority_nodes: list[dict], quads: list[Quad] | list[dict]) -> dict:
    """Simulate impact propagation starting from priority subjects."""
    serialized_quads = [
        q.model_dump() if hasattr(q, "model_dump") else q
        for q in quads
    ]
    mcp_res = _invoke_mcp_tool("graph_quadstore_impact_analysis", {"priority_nodes": priority_nodes, "quads": serialized_quads})
    if mcp_res is not None:
        return mcp_res

    print(f"    [tool] tool_quadstore_impact_analysis()")
    priority_ids = {n["id"] for n in priority_nodes}
    affected = {q.object if hasattr(q, "object") else q.get("object") for q in quads if (q.subject if hasattr(q, "subject") else q.get("subject")) in priority_ids}
    return {"affected_entities": list(affected)}


def tool_dispatch_action(action: dict) -> bool:
    """Simulate REST/gRPC dispatch of a decision action."""
    mcp_res = _invoke_mcp_tool("graph_dispatch_action", {"action": action})
    if mcp_res is not None:
        return bool(mcp_res.get("success", True) if isinstance(mcp_res, dict) else mcp_res)

    print(f"    [tool] dispatch_action(type={action.get('type')!r})")
    return True