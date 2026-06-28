# Connecting to the Apache AGE MCP Server

This guide explains how to connect various LLM agents and clients to the local **Apache AGE MCP Server** (`Scripts/mcp/age_mcp_server.py`) you just created.

The MCP (Model Context Protocol) Server operates over standard input/output (`stdio`) and provides tools for an LLM to read, write, and execute Cypher queries natively on your Apache AGE `memory_db` quadstore graph.

---

## 1. Prerequisites
Ensure the `mcp` Python package is installed in your backend environment before attempting to connect an agent:
```bash
uv pip install mcp
```

---

## 2. Connecting Claude Desktop
If you are using the Claude Desktop application, you can configure it to spin up and attach to this MCP server automatically.

1. Open your Claude Desktop configuration file:
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Add the following entry to your `mcpServers` block:

```json
{
  "mcpServers": {
    "apache-age": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "C:\\CalismaAlani\\CodingPython\\Bitirme\\backend\\Scripts\\mcp\\age_mcp_server.py"
      ]
    }
  }
}
```
3. Restart Claude Desktop. You will now see a "hammer" icon indicating the tools (`execute_cypher`, `create_node`, etc.) are available for Claude to use in conversations.

---

## 3. Connecting Cursor IDE
If you use the Cursor IDE and want its built-in Composer/Agent to interact with your graph:

1. Open **Cursor Settings** -> **Features** -> **MCP Servers**.
2. Click **+ Add new MCP server**.
3. Configure the fields as follows:
   - **Type:** `command`
   - **Name:** `ApacheAGE`
   - **Command:** `uv run python C:\CalismaAlani\CodingPython\Bitirme\backend\Scripts\mcp\age_mcp_server.py`
4. Click **Save**. Cursor will connect to the server and surface the graph tools directly to your AI chats.

---

## 4. Connecting a Custom Python Agent
If you are building your own agent in Python (e.g., using LangChain, LlamaIndex, or raw LLM API calls), you can use the official `mcp` client library to connect to the server.

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_agent():
    # Define the parameters to start the MCP server
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "Scripts/mcp/age_mcp_server.py"],
    )

    # Start the server process and establish a session
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # 1. Discover available tools
            tools = await session.list_tools()
            print("Available Graph Tools:", [t.name for t in tools])

            # 2. Call a tool (e.g., checking the schema)
            result = await session.call_tool("get_graph_schema", {})
            print("Graph Schema:", result.content)

            # 3. Call a tool with parameters
            node_result = await session.call_tool("create_node", {
                "label": "AgentMemory",
                "properties": {"concept": "Artificial Intelligence", "confidence": 0.95}
            })
            print("Node Creation Result:", node_result.content)

if __name__ == "__main__":
    asyncio.run(run_agent())
```

---

## Available Tools Reference
Once connected, your agent will have access to the following tools:

- `get_graph_schema()`: Read existing node labels and edge types.
- `create_node(label, properties)`: Create a new graph node.
- `update_node(node_id, properties)`: Modify properties on an existing node.
- `delete_node(node_id)`: Delete a node (and detach all its relationships).
- `create_edge(start_node_id, edge_label, end_node_id, properties)`: Connect two nodes together.
- `delete_edge(edge_id)`: Remove a specific relationship.
- `execute_cypher(query, params)`: Send raw Cypher syntax securely via parameterized inputs for complex sub-graph retrieval.
