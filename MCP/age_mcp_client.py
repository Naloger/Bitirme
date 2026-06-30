# -*- coding: utf-8 -*-
"""
Python agent client for the Apache AGE MCP server.
Connects via stdio — spawns the server as a subprocess.
Designed for local WSL + Podman environments.

Usage:
    python age_mcp_client.py
    python age_mcp_client.py --script examples/seed_graph.py
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from mcp import ClientSession, StdioServerParameters

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("age_client")

# ── Server location ───────────────────────────────────────────────────────────
# Adjust this to wherever your MCP server script lives.
# Works whether you run from WSL native path or a Podman-mounted volume.

SERVER_SCRIPT = (
    Path(__file__).resolve().parent.parent.parent / "backend" / "MCP" / "age_mcp_server.py"
)
if not SERVER_SCRIPT.exists():
    SERVER_SCRIPT = Path(__file__).resolve().parent / "age_mcp_server.py"


# ── Low-level tool call ───────────────────────────────────────────────────────

async def call_tool(session: ClientSession, name: str, **kwargs: Any) -> Any:
    """
    Call a single MCP tool and return the parsed result.
    Raises RuntimeError on tool-level errors so callers can handle them cleanly.
    """
    # Strip None kwargs — MCP servers behave differently on absent vs null params
    args = {k: v for k, v in kwargs.items() if v is not None}

    log.debug("→ %s(%s)", name, args)
    result = await session.call_tool(name, arguments=args)

    # Extract text from the first TextContent block
    text = ""
    for block in result.content:
        if isinstance(block, TextContent):
            text = block.text
            break

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text  # return raw string if not JSON

    if isinstance(parsed, dict) and parsed.get("status") in ("error", "warning"):
        status_val = parsed.get("status")
        msg = parsed.get("message", text)
        raise RuntimeError(f"Tool '{name}' {status_val}: {msg}")

    log.debug("← %s", json.dumps(parsed, indent=2))
    return parsed


# ── Typed tool wrappers ───────────────────────────────────────────────────────
# These mirror the server tools exactly so you get IDE completion and type safety.

class AGEClient:
    """High-level async client wrapping every AGE MCP tool."""

    def __init__(self, session: ClientSession):
        self._s = session

    # ── Schema ────────────────────────────────────────────────────────────────

    async def get_schema(self) -> dict:
        return await call_tool(self._s, "get_graph_schema")

    # ── Raw Cypher ────────────────────────────────────────────────────────────

    async def cypher(
        self,
        query: str,
        params: dict | None = None,
        col_defs: str | None = None,
    ) -> Any:
        return await call_tool(
            self._s,
            "execute_cypher",
            query=query,
            params=params,
            col_defs=col_defs,
        )

    # ── Nodes ─────────────────────────────────────────────────────────────────

    async def create_node(self, label: str, properties: dict | None = None) -> dict:
        return await call_tool(self._s, "create_node", label=label, properties=properties)

    async def update_node(self, node_id: int, properties: dict) -> dict:
        return await call_tool(self._s, "update_node", node_id=node_id, properties=properties)

    async def delete_node(self, node_id: int) -> dict:
        return await call_tool(self._s, "delete_node", node_id=node_id)

    # ── Edges ─────────────────────────────────────────────────────────────────

    async def create_edge(
        self,
        start_node_id: int,
        edge_label: str,
        end_node_id: int,
        properties: dict | None = None,
    ) -> dict:
        return await call_tool(
            self._s,
            "create_edge",
            start_node_id=start_node_id,
            edge_label=edge_label,
            end_node_id=end_node_id,
            properties=properties,
        )

    async def delete_edge(self, edge_id: int) -> dict:
        return await call_tool(self._s, "delete_edge", edge_id=edge_id)

    # ── Convenience helpers ───────────────────────────────────────────────────

    async def find_nodes(self, label: str, limit: int = 20) -> list:
        result = await self.cypher(
            f"MATCH (n:{label}) RETURN n LIMIT {limit}"
        )
        return result.get("results", [])

    async def find_path(self, start_name: str, end_name: str, max_hops: int = 4) -> list:
        result = await self.cypher(
            "MATCH path = shortestPath((a)-[*1..$hops]->(b)) "
            "WHERE a.name = $start AND b.name = $end RETURN path",
            params={"start": start_name, "end": end_name, "hops": max_hops},
        )
        return result.get("results", [])

    # ── RDF Quadstore Helpers ─────────────────────────────────────────────────

    async def add_quad(
        self,
        subject: dict,
        predicate: str,
        obj: dict,
        context: str,
    ) -> Any:
        """
        Add a single RDF quad to the quadstore.
        
        subject: dict with keys:
            - 'type': 'iri' or 'bnode'
            - 'value': URI string or blank node ID
        predicate: URI string of the predicate
        obj: dict with keys:
            - 'type': 'iri', 'bnode' or 'literal'
            - 'value': URI string / blank node ID, or the string value of the literal
            - 'datatype': (Optional) string datatype URI for literals
            - 'lang': (Optional) string language tag for literals
        context: URI string of the named graph / context
        """
        is_literal = obj.get("type") == "literal"
        if is_literal:
            params = {
                "subject": {"value": subject["value"], "type": subject["type"]},
                "predicate": predicate,
                "object": {
                    "value": str(obj["value"]),
                    "datatype": str(obj.get("datatype") or "http://www.w3.org/2001/XMLSchema#string"),
                    "lang": str(obj.get("lang") or "")
                },
                "context": context
            }
            query = """
            MERGE (s:RDFResource {uri: $subject.value, type: $subject.type})
            MERGE (o:RDFLiteral {value: $object.value, datatype: $object.datatype, lang: $object.lang})
            MERGE (s)-[r:RDF_EDGE {predicate: $predicate, context: $context}]->(o)
            RETURN r
            """
        else:
            params = {
                "subject": {"value": subject["value"], "type": subject["type"]},
                "predicate": predicate,
                "object": {"value": obj["value"], "type": obj["type"]},
                "context": context
            }
            query = """
            MERGE (s:RDFResource {uri: $subject.value, type: $subject.type})
            MERGE (o:RDFResource {uri: $object.value, type: $object.type})
            MERGE (s)-[r:RDF_EDGE {predicate: $predicate, context: $context}]->(o)
            RETURN r
            """
        return await self.cypher(query, params=params)

    async def query_quads(
        self,
        subject: str | None = None,
        predicate: str | None = None,
        obj_value: str | None = None,
        context: str | None = None,
    ) -> list:
        """Query quads matching the given patterns (None acts as wildcard)."""
        cypher_query = "MATCH (s:RDFResource)-[r:RDF_EDGE]->(o) "
        where_clauses = []
        params = {}

        if subject:
            where_clauses.append("s.uri = $subject")
            params["subject"] = subject

        if predicate:
            where_clauses.append("r.predicate = $predicate")
            params["predicate"] = predicate

        if context:
            where_clauses.append("r.context = $context")
            params["context"] = context

        if obj_value:
            where_clauses.append("(o.uri = $obj_val OR o.value = $obj_val)")
            params["obj_val"] = obj_value

        if where_clauses:
            cypher_query += "WHERE " + " AND ".join(where_clauses) + " "

        cypher_query += (
            "RETURN { "
            "subject: {uri: s.uri, type: s.type}, "
            "predicate: r.predicate, "
            "object: {uri: o.uri, value: o.value, datatype: o.datatype, lang: o.lang, labels: labels(o)}, "
            "context: r.context "
            "}"
        )
        result = await self.cypher(cypher_query, params=params)
        return result.get("results", [])


# ── Agent task runner ─────────────────────────────────────────────────────────

async def run_demo(client: AGEClient) -> None:
    """
    Example agent task: inspect schema, seed a small subgraph, query it,
    then seed and query RDF quads matching the backend quadstore schema.
    """
    log.info("── Schema inspection ──────────────────────────────────")
    schema = await client.get_schema()
    print(json.dumps(schema, indent=2))

    log.info("── LPG operations ─────────────────────────────────────")
    log.info("── Creating nodes ─────────────────────────────────────")
    ai_node   = await client.create_node("Concept", {"name": "Artificial Intelligence", "weight": 0.9})
    ml_node   = await client.create_node("Concept", {"name": "Machine Learning",        "weight": 0.85})
    nlp_node  = await client.create_node("Concept", {"name": "Natural Language Processing", "weight": 0.8})

    # Extract the internal graph IDs from the returned agtype data
    ai_id  = _extract_id(ai_node)
    ml_id  = _extract_id(ml_node)
    nlp_id = _extract_id(nlp_node)

    log.info("Created nodes — AI:%s  ML:%s  NLP:%s", ai_id, ml_id, nlp_id)

    log.info("── Creating edges ─────────────────────────────────────")
    await client.create_edge(ai_id,  "INCLUDES", ml_id,  {"weight": 0.9})
    await client.create_edge(ai_id,  "INCLUDES", nlp_id, {"weight": 0.8})
    await client.create_edge(ml_id,  "ENABLES",  nlp_id, {"weight": 0.7})

    log.info("── Querying neighbourhood ─────────────────────────────")
    result = await client.cypher(
        "MATCH (a:Concept)-[r]->(b:Concept) "
        "WHERE a.name = $name "
        "RETURN {a_name: a.name, rel_type: type(r), b_name: b.name, weight: r.weight}",
        params={"name": "Artificial Intelligence"},
    )
    print(json.dumps(result, indent=2))

    log.info("── Updating a node ────────────────────────────────────")
    await client.update_node(ml_id, {"description": "Subset of AI using statistical learning"})

    log.info("── RDF Quadstore operations ───────────────────────────")
    log.info("── Seeding RDF Quads ──────────────────────────────────")
    subject = {"value": "http://example.org/concept/AI", "type": "iri"}
    obj = {"value": "http://example.org/concept/ML", "type": "iri"}
    await client.add_quad(
        subject=subject,
        predicate="http://example.org/relation/includes",
        obj=obj,
        context="http://example.org/graph/main"
    )

    literal_obj = {
        "value": "Artificial Intelligence",
        "type": "literal",
        "datatype": "http://www.w3.org/2001/XMLSchema#string",
        "lang": "en"
    }
    await client.add_quad(
        subject=subject,
        predicate="http://example.org/relation/label",
        obj=literal_obj,
        context="http://example.org/graph/main"
    )

    log.info("── Querying Quadstore ─────────────────────────────────")
    quads = await client.query_quads(subject="http://example.org/concept/AI")
    print(json.dumps(quads, indent=2))

    log.info("── Raw schema after seeding ───────────────────────────")
    print(json.dumps(await client.get_schema(), indent=2))


def _extract_id(tool_result: dict) -> int:
    """
    Pull the internal AGE graph ID from a create_node / create_edge result.
    AGE returns agtype objects; the id is nested under data[0]["id"].
    Adjust this if your parse_agtype returns a different shape.
    """
    try:
        data = tool_result["data"]
        if isinstance(data, list) and data:
            node = data[0]
            if isinstance(node, dict):
                return node.get("id") or node.get("properties", {}).get("id")
    except (KeyError, IndexError, TypeError):
        pass
    raise ValueError(f"Cannot extract ID from result: {tool_result}")


# ── REPL (interactive fallback) ───────────────────────────────────────────────

async def run_repl(client: AGEClient) -> None:
    """Minimal interactive Cypher REPL for ad-hoc exploration."""
    print("Apache AGE Cypher REPL  (type 'exit' to quit, ':schema' for schema)")
    while True:
        try:
            line = input("cypher> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not line:
            continue
        if line.lower() in ("exit", "quit", ":q"):
            break
        if line == ":schema":
            print(json.dumps(await client.get_schema(), indent=2))
            continue

        try:
            result = await client.cypher(line)
            print(json.dumps(result, indent=2))
        except RuntimeError as exc:
            print(f"ERROR: {exc}")


# ── Entry point ───────────────────────────────────────────────────────────────

async def main(mode: str) -> None:
    if not SERVER_SCRIPT.exists():
        log.error("Server script not found: %s", SERVER_SCRIPT)
        log.error("Set SERVER_SCRIPT at the top of this file to the correct path.")
        sys.exit(1)

    # Locate the python interpreter in the backend virtualenv if available
    backend_dir = SERVER_SCRIPT.parent.parent
    command_executable = backend_dir / ".venv" / "Scripts" / "python.exe"
    if not command_executable.exists():
        command_executable = backend_dir / ".venv" / "bin" / "python"
    if not command_executable.exists():
        command_executable = Path(sys.executable)

    server_params = StdioServerParameters(
        command=str(command_executable),
        args=[str(SERVER_SCRIPT)],
        # Pass through the current environment so WSL paths, PYTHONPATH,
        # and Podman socket vars (DOCKER_HOST etc.) are all visible to the server.
        env=dict(os.environ),
    )

    log.info("Spawning MCP server: %s", SERVER_SCRIPT)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            log.info("Connected — %d tools available: %s",
                     len(tools.tools),
                     [t.name for t in tools.tools])

            client = AGEClient(session)

            if mode == "repl":
                await run_repl(client)
            else:
                await run_demo(client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apache AGE MCP agent client")
    parser.add_argument(
        "--mode",
        choices=["demo", "repl"],
        default="demo",
        help="demo: run the seeding example  |  repl: interactive Cypher shell",
    )
    args = parser.parse_args()
    asyncio.run(main(args.mode))