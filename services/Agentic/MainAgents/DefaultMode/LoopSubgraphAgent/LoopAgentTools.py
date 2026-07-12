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
import warnings
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
        warnings.warn(f"MCP is disabled. Local fallback for '{tool_name}' will be used.", UserWarning)
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

def tool_ingest_internal_stream(source: str = "knowledge_graph", sample_size: int | None = None) -> list[dict]:
    """Recall internal statements from the knowledge graph, optionally sampling N random quads."""
    args = {"source": source}
    if sample_size is not None:
        args["sample_size"] = sample_size
    mcp_res = _invoke_mcp_tool("graph_ingest_internal_stream", args)
    if mcp_res is not None:
        return mcp_res

    warnings.warn(f"MCP tool 'graph_ingest_internal_stream' not available. Local fallback returns empty list.", UserWarning)
    return []


def tool_ingest_external_api(endpoint: str = "llm_input", sample_size: int | None = None) -> list[dict]:
    """Ingest standard LLM input text."""
    args = {"endpoint": endpoint}
    if sample_size is not None:
        args["sample_size"] = sample_size
    mcp_res = _invoke_mcp_tool("graph_ingest_external_api", args)
    if mcp_res is not None:
        return mcp_res

    warnings.warn(f"MCP tool 'graph_ingest_external_api' not available. Local fallback returns empty list.", UserWarning)
    return []


def tool_write_to_quadstore(
    quads: list[Quad] | list[dict],
    overwrite: bool = False,
    clear_contexts: list[str] | None = None
) -> bool:
    """Atomic RDF quad creation/insertion into a triplestore/quadstore."""
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

    warnings.warn(f"MCP tool 'graph_write_to_quadstore' not available. Writing {len(quads)} quads locally to console only.", UserWarning)
    for q in quads:
        subject = q.subject if hasattr(q, "subject") else q.get("subject")
        predicate = q.predicate if hasattr(q, "predicate") else q.get("predicate")
        obj = q.object if hasattr(q, "object") else q.get("object")
        graph = q.graph if hasattr(q, "graph") else q.get("graph")
        print(f"      • Quad: ({subject}, {predicate}, {obj}) inside Graph URI: {graph}")
    return True


# ── Organizer tools ──────────────────────────────────────────────────────────

def tool_run_community_detection(quads: list[Quad] | list[dict]) -> list[dict]:
    """Community/cluster grouping of subjects from atomic quads."""
    serialized_quads = [
        q.model_dump() if hasattr(q, "model_dump") else q
        for q in quads
    ]
    mcp_res = _invoke_mcp_tool("graph_run_community_detection", {"quads": serialized_quads})
    if mcp_res is not None:
        return mcp_res

    warnings.warn(f"MCP tool 'graph_run_community_detection' not available. Local fallback returns empty list.", UserWarning)
    return []


def tool_map_ontology(quads: list[Quad] | list[dict], ontology: str = "default") -> list[dict]:
    """OWL/RDF ontology checking — assign concept metadata to quads."""
    serialized_quads = [
        q.model_dump() if hasattr(q, "model_dump") else q
        for q in quads
    ]
    mcp_res = _invoke_mcp_tool("graph_map_ontology", {"quads": serialized_quads, "ontology": ontology})
    if mcp_res is not None:
        return mcp_res

    warnings.warn(f"MCP tool 'graph_map_ontology' not available. Local fallback returns empty list.", UserWarning)
    return []


def tool_index_quads(quads: list[Quad] | list[dict]) -> dict:
    """Vector or elasticsearch indexing on atomic RDF statements."""
    serialized_quads = [
        q.model_dump() if hasattr(q, "model_dump") else q
        for q in quads
    ]
    mcp_res = _invoke_mcp_tool("graph_index_quads", {"quads": serialized_quads})
    if mcp_res is not None:
        return mcp_res

    warnings.warn(f"MCP tool 'graph_index_quads' not available. Local fallback returns empty dict.", UserWarning)
    return {}


# ── Reflector tools ──────────────────────────────────────────────────────────

def tool_validate_quads(quads: list[Quad] | list[dict]) -> list[dict]:
    """SHACL / constraint-language validation on atomic RDF quads."""
    serialized_quads = [
        q.model_dump() if hasattr(q, "model_dump") else q
        for q in quads
    ]
    mcp_res = _invoke_mcp_tool("graph_validate_quads", {"quads": serialized_quads})
    if mcp_res is not None:
        return mcp_res

    warnings.warn(f"MCP tool 'graph_validate_quads' not available. Local fallback returns empty list.", UserWarning)
    return []


def tool_detect_anomalies(quads: list[Quad] | list[dict]) -> list[str]:
    """GNN-based anomaly detection over the RDF quad linkages."""
    serialized_quads = [
        q.model_dump() if hasattr(q, "model_dump") else q
        for q in quads
    ]
    mcp_res = _invoke_mcp_tool("graph_detect_anomalies", {"quads": serialized_quads})
    if mcp_res is not None:
        return mcp_res

    warnings.warn(f"MCP tool 'graph_detect_anomalies' not available. Local fallback returns empty list.", UserWarning)
    return []


def tool_infer_missing_quads(quads: list[Quad] | list[dict], issues: list[dict]) -> list[dict]:
    """Suggest inferred RDF quads based on structured relations."""
    serialized_quads = [
        q.model_dump() if hasattr(q, "model_dump") else q
        for q in quads
    ]
    mcp_res = _invoke_mcp_tool("graph_infer_missing_quads", {"quads": serialized_quads, "issues": issues})
    if mcp_res is not None:
        return mcp_res

    warnings.warn(f"MCP tool 'graph_infer_missing_quads' not available. Local fallback returns empty list.", UserWarning)
    return []


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

    warnings.warn(f"MCP tool 'graph_quadstore_traversal' not available. Local fallback returns empty list.", UserWarning)
    return []


def tool_quadstore_impact_analysis(priority_nodes: list[dict], quads: list[Quad] | list[dict]) -> dict:
    """Impact propagation starting from priority subjects."""
    serialized_quads = [
        q.model_dump() if hasattr(q, "model_dump") else q
        for q in quads
    ]
    mcp_res = _invoke_mcp_tool("graph_quadstore_impact_analysis", {"priority_nodes": priority_nodes, "quads": serialized_quads})
    if mcp_res is not None:
        return mcp_res

    warnings.warn(f"MCP tool 'graph_quadstore_impact_analysis' not available. Local fallback returns empty impact set.", UserWarning)
    return {"affected_entities": []}


def tool_dispatch_action(action: dict) -> bool:
    """REST/gRPC dispatch of a decision action."""
    mcp_res = _invoke_mcp_tool("graph_dispatch_action", {"action": action})
    if mcp_res is not None:
        return bool(mcp_res.get("success", True) if isinstance(mcp_res, dict) else mcp_res)

    warnings.warn(f"MCP tool 'graph_dispatch_action' not available. Action dispatch fallback is disabled.", UserWarning)
    return True