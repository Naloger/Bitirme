# -*- coding: utf-8 -*-
"""Script to extract and visualize Apache AGE graphs in an interactive browser-based UI."""

import json
import os
import sys
import psycopg2
from typing import Dict, List, Any
from pathlib import Path


# Configure stdout to use UTF-8 to support Windows console output
if sys.stdout.encoding != 'utf-8':
    reconfigure_stdout = getattr(sys.stdout, 'reconfigure', None)
    if reconfigure_stdout:
        try:
            reconfigure_stdout(encoding='utf-8')
        except Exception:
            pass


# Add backend directory to Python path if running script directly
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from Scripts.infra.age.age_helpers import (
    PG_HOST,
    PG_PORT,
    PG_USER,
    PG_PASSWORD,
    DEFAULT_DB,
    parse_agtype
)



def get_all_age_databases() -> List[str]:
    """Query PostgreSQL to find all user databases."""
    databases = []
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=DEFAULT_DB,
            user=PG_USER,
            password=PG_PASSWORD
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("""
                SELECT d.datname
                FROM pg_catalog.pg_database d
                WHERE d.datistemplate = false
                ORDER BY d.datname;
            """)
            databases = [row[0] for row in cur.fetchall()]
        conn.close()
    except Exception as e:
        print(f"❌ Error listing databases: {e}")
    return databases


def get_graphs_in_db(db_name: str) -> List[str]:
    """Check if the 'age' extension exists and list all graphs in the database."""
    graphs = []
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=db_name,
            user=PG_USER,
            password=PG_PASSWORD
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            # Check if age extension exists
            cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'age';")
            if not cur.fetchone():
                conn.close()
                return []
            
            # Load age and search_path
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, '$user', public;")
            
            # Query graphs
            cur.execute("SELECT name FROM ag_graph;")
            graphs = [row[0] for row in cur.fetchall()]
        conn.close()
    except Exception:
        # DB might not be initialized or accessible yet
        pass
    return graphs


def fetch_graph_data(db_name: str, graph_name: str) -> Dict[str, List[Any]]:
    """Fetch all nodes and edges from a specific Apache AGE graph."""
    nodes = []
    edges = []
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=db_name,
            user=PG_USER,
            password=PG_PASSWORD
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, '$user', public;")
            
            # 1. Fetch nodes
            cur.execute(f"""
                SELECT * FROM cypher('{graph_name}', $$
                    MATCH (n)
                    RETURN id(n), labels(n), properties(n)
                $$) as (id agtype, labels agtype, props agtype);
            """)
            node_rows = cur.fetchall()
            for r in node_rows:
                n_id = parse_agtype(r[0])
                n_labels = parse_agtype(r[1]) or []
                n_props = parse_agtype(r[2]) or {}
                nodes.append({
                    "id": str(n_id),
                    "labels": n_labels,
                    "properties": n_props
                })
            
            # 2. Fetch edges
            cur.execute(f"""
                SELECT * FROM cypher('{graph_name}', $$
                    MATCH (a)-[r]->(b)
                    RETURN id(a), id(b), type(r), properties(r)
                $$) as (src agtype, tgt agtype, type agtype, props agtype);
            """)
            edge_rows = cur.fetchall()
            for r in edge_rows:
                src_id = parse_agtype(r[0])
                tgt_id = parse_agtype(r[1])
                e_type = parse_agtype(r[2])
                e_props = parse_agtype(r[3]) or {}
                edges.append({
                    "source": str(src_id),
                    "target": str(tgt_id),
                    "type": e_type,
                    "properties": e_props
                })
        conn.close()
    except Exception as e:
        print(f"⚠️ Error fetching graph '{graph_name}' in db '{db_name}': {e}")
        
    return {"nodes": nodes, "edges": edges}


def main():
    print("🔌 Scanning Apache AGE PostgreSQL databases...")
    databases = get_all_age_databases()
    
    all_graph_data = {}
    
    for db in databases:
        graphs = get_graphs_in_db(db)
        if not graphs:
            continue
        print(f"📂 Found database '{db}' with graphs: {graphs}")
        for graph in graphs:
            key = f"{db} / {graph}"
            print(f"   📥 Fetching schema nodes and edges for '{key}'...")
            data = fetch_graph_data(db, graph)
            all_graph_data[key] = data
            print(f"      Loaded {len(data['nodes'])} nodes, {len(data['edges'])} edges.")
            
    if not all_graph_data:
        print("❌ No Apache AGE graphs found to visualize.")
        sys.exit(1)
        
    # Write interactive HTML visualization
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_html_path = os.path.join(script_dir, "visualize_graphs.html")
    
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apache AGE Graph Visualization</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #0f172a;
            color: #f1f5f9;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        header {
            background-color: #1e293b;
            border-bottom: 1px solid #334155;
            padding: 15px 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 10;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        .header-title h1 {
            font-size: 1.4rem;
            font-weight: 700;
            background: linear-gradient(135deg, #3b82f6, #60a5fa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header-title p {
            font-size: 0.8rem;
            color: #94a3b8;
            margin-top: 2px;
        }
        .selector-container {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .selector-container label {
            font-size: 0.9rem;
            font-weight: 500;
            color: #cbd5e1;
        }
        select {
            background-color: #0f172a;
            color: #f1f5f9;
            border: 1px solid #475569;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 0.9rem;
            font-weight: 600;
            outline: none;
            cursor: pointer;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        select:focus {
            border-color: #3b82f6;
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25);
        }
        .app-container {
            flex: 1;
            display: flex;
            position: relative;
            height: calc(100vh - 75px);
        }
        #network-container {
            flex: 1;
            height: 100%;
            background-color: #090d16;
        }
        .sidebar {
            width: 360px;
            background-color: #1e293b;
            border-left: 1px solid #334155;
            display: flex;
            flex-direction: column;
            height: 100%;
            z-index: 5;
            transition: transform 0.3s ease;
            box-shadow: -4px 0 10px -3px rgba(0, 0, 0, 0.2);
        }
        .sidebar-section {
            padding: 20px;
            border-bottom: 1px solid #334155;
        }
        .sidebar-section h2 {
            font-size: 1.1rem;
            font-weight: 600;
            color: #cbd5e1;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .meta-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        .meta-card {
            background-color: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px;
            text-align: center;
        }
        .meta-card .num {
            font-size: 1.6rem;
            font-weight: 700;
            color: #3b82f6;
        }
        .meta-card .label {
            font-size: 0.75rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 4px;
        }
        .properties-detail {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }
        .properties-detail p.placeholder {
            color: #64748b;
            font-style: italic;
            text-align: center;
            margin-top: 40px;
        }
        .detail-card {
            background-color: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .detail-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            border-bottom: 1px solid #334155;
            padding-bottom: 8px;
        }
        .detail-header h3 {
            font-size: 0.95rem;
            color: #3b82f6;
        }
        .label-badge {
            background-color: #1e293b;
            border: 1px solid #475569;
            color: #94a3b8;
            font-size: 0.7rem;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: bold;
        }
        .prop-row {
            display: flex;
            flex-direction: column;
            gap: 4px;
            margin-bottom: 10px;
        }
        .prop-key {
            font-size: 0.75rem;
            color: #64748b;
            font-weight: 600;
            text-transform: uppercase;
        }
        .prop-val {
            font-size: 0.85rem;
            color: #e2e8f0;
            word-break: break-all;
            background-color: #1e293b;
            padding: 6px 8px;
            border-radius: 4px;
            font-family: monospace;
        }
        .controls-panel {
            position: absolute;
            bottom: 20px;
            left: 20px;
            background-color: rgba(30, 41, 59, 0.85);
            backdrop-filter: blur(8px);
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px;
            display: flex;
            gap: 10px;
            align-items: center;
            z-index: 10;
        }
        .btn {
            background-color: #3b82f6;
            color: #f1f5f9;
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .btn:hover {
            background-color: #2563eb;
        }
        .btn-secondary {
            background-color: #475569;
        }
        .btn-secondary:hover {
            background-color: #334155;
        }
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <h1>Apache AGE Graph Explorer</h1>
            <p>Interactive graph database schema visualization</p>
        </div>
        <div class="selector-container">
            <label for="graph-selector">Select Graph:</label>
            <select id="graph-selector" onchange="loadSelectedGraph()">
                <!-- Graphs will be dynamically populated -->
            </select>
        </div>
    </header>

    <div class="app-container">
        <div id="network-container"></div>
        
        <div class="controls-panel">
            <button class="btn" id="physics-btn" onclick="togglePhysics()">Pause Physics</button>
            <button class="btn btn-secondary" onclick="fitNetwork()">Zoom Fit</button>
        </div>

        <div class="sidebar">
            <div class="sidebar-section">
                <h2>📊 Graph Info</h2>
                <div class="meta-grid">
                    <div class="meta-card">
                        <div class="num" id="node-count">0</div>
                        <div class="label">Nodes</div>
                    </div>
                    <div class="meta-card">
                        <div class="num" id="edge-count">0</div>
                        <div class="label">Edges</div>
                    </div>
                </div>
            </div>
            <div class="properties-detail" id="detail-pane">
                <h2>🔍 Selection Detail</h2>
                <p class="placeholder">Click on a node or edge to inspect properties</p>
            </div>
        </div>
    </div>

    <script>
        const rawData = {{DATA}};
        let network = null;
        let physicsEnabled = true;

        // Populate Graph Select dropdown
        const selector = document.getElementById("graph-selector");
        Object.keys(rawData).forEach(key => {
            const opt = document.createElement("option");
            opt.value = key;
            opt.innerText = key;
            selector.appendChild(opt);
        });

        // Color palettes
        const COLORS = {
            Keyword: { background: "#14b8a6", border: "#0d9488", highlight: { background: "#2dd4bf", border: "#14b8a6" } }, // Teal
            RDFResource: { background: "#3b82f6", border: "#2563eb", highlight: { background: "#60a5fa", border: "#3b82f6" } }, // Blue
            RDFLiteral: { background: "#f59e0b", border: "#d97706", highlight: { background: "#fbbf24", border: "#f59e0b" } }, // Amber
            Concept: { background: "#ec4899", border: "#db2777", highlight: { background: "#f472b6", border: "#ec4899" } }, // Pink
            default: { background: "#64748b", border: "#475569", highlight: { background: "#94a3b8", border: "#64748b" } } // Slate
        };

        function shortenUri(uri) {
            if (!uri) return "";
            try {
                const url = new URL(uri);
                // Return short namespace:localName or just pathname end
                const pathParts = url.pathname.split('/');
                const lastPart = pathParts[pathParts.length - 1];
                if (url.hash) {
                    return url.hash.substring(1);
                }
                return lastPart || url.hostname;
            } catch (e) {
                // If it's a blank node or not a URL
                return uri.length > 25 ? uri.substring(0, 25) + "..." : uri;
            }
        }

        function loadSelectedGraph() {
            const key = selector.value;
            if (!key || !rawData[key]) return;

            const graph = rawData[key];
            
            // Update UI metadata
            document.getElementById("node-count").innerText = graph.nodes.length;
            document.getElementById("edge-count").innerText = graph.edges.length;
            resetDetailPane();

            // Transform Nodes
            const visNodes = graph.nodes.map(n => {
                const labelType = n.labels[0] || "default";
                const palette = COLORS[labelType] || COLORS.default;
                
                // Label string based on type
                let displayLabel = "";
                let title = n.labels.join(", ");
                
                if (labelType === "Keyword") {
                    displayLabel = n.properties.word || `Node ${n.id}`;
                } else if (labelType === "RDFResource") {
                    displayLabel = shortenUri(n.properties.uri) || `Resource ${n.id}`;
                    title += `\\nURI: ${n.properties.uri}`;
                } else if (labelType === "RDFLiteral") {
                    displayLabel = n.properties.value;
                    if (displayLabel && displayLabel.length > 15) {
                        displayLabel = displayLabel.substring(0, 15) + "...";
                    }
                    title += `\\nValue: ${n.properties.value}\\nDatatype: ${n.properties.datatype || "string"}`;
                    if (n.properties.lang) title += `\\nLang: ${n.properties.lang}`;
                } else {
                    displayLabel = n.properties.name || n.properties.label || `Node ${n.id}`;
                }

                return {
                    id: n.id,
                    label: displayLabel,
                    title: title,
                    color: palette,
                    shape: labelType === "RDFLiteral" ? "box" : "dot",
                    size: labelType === "RDFLiteral" ? 20 : 16,
                    font: { color: "#f1f5f9", size: 12 },
                    rawData: n
                };
            });

            // Transform Edges
            const visEdges = graph.edges.map((e, idx) => {
                let displayLabel = e.type || "";
                let weight = 1;
                let title = `Type: ${e.type}`;

                // Extract PPMI co-occurrence weights
                if (e.properties && e.properties.weight !== undefined) {
                    weight = parseFloat(e.properties.weight);
                    displayLabel = `${displayLabel} (${weight.toFixed(2)})`;
                    title += `\\nWeight: ${weight}`;
                }
                
                // Extract RDF predicate
                if (e.properties && e.properties.predicate) {
                    displayLabel = shortenUri(e.properties.predicate);
                    title += `\\nPredicate: ${e.properties.predicate}`;
                    if (e.properties.context) title += `\\nContext/Graph: ${e.properties.context}`;
                }

                return {
                    id: `edge_${idx}`,
                    from: e.source,
                    to: e.target,
                    label: displayLabel,
                    title: title,
                    arrows: (e.type === "CO_OCCUR_WITH") ? "" : "to", // Undirected for co-occurrences, directed for RDF/Concepts
                    width: Math.min(Math.max(weight * 1.5, 1), 6),
                    color: { color: "#475569", highlight: "#3b82f6", hover: "#60a5fa" },
                    font: { color: "#94a3b8", size: 10, strokeWidth: 0, align: "horizontal" },
                    rawData: e
                };
            });

            const container = document.getElementById("network-container");
            const data = {
                nodes: new vis.DataSet(visNodes),
                edges: new vis.DataSet(visEdges)
            };

            const options = {
                nodes: {
                    borderWidth: 2,
                    scaling: { min: 10, max: 30 }
                },
                edges: {
                    smooth: {
                        type: "continuous",
                        roundness: 0.5
                    }
                },
                physics: {
                    enabled: true,
                    stabilization: {
                        enabled: true,
                        iterations: 150
                    },
                    barnesHut: {
                        gravitationalConstant: -3000,
                        centralGravity: 0.3,
                        springLength: 120,
                        springConstant: 0.04,
                        damping: 0.09
                    }
                },
                interaction: {
                    hover: true,
                    tooltipDelay: 200
                }
            };

            if (network) {
                network.destroy();
            }

            network = new vis.Network(container, data, options);
            physicsEnabled = true;
            document.getElementById("physics-btn").innerText = "Pause Physics";
            document.getElementById("physics-btn").classList.remove("btn-secondary");

            // Register click handlers
            network.on("click", function (params) {
                if (params.nodes.length > 0) {
                    const clickedNodeId = params.nodes[0];
                    const nodeData = data.nodes.get(clickedNodeId);
                    showNodeDetails(nodeData.rawData);
                } else if (params.edges.length > 0) {
                    const clickedEdgeId = params.edges[0];
                    const edgeData = data.edges.get(clickedEdgeId);
                    showEdgeDetails(edgeData.rawData);
                } else {
                    resetDetailPane();
                }
            });
        }

        function showNodeDetails(node) {
            const pane = document.getElementById("detail-pane");
            
            let labelBadges = node.labels.map(l => `<span class="label-badge">${l}</span>`).join(" ");
            
            let propsHtml = "";
            Object.keys(node.properties).forEach(k => {
                propsHtml += `
                    <div class="prop-row">
                        <span class="prop-key">${k}</span>
                        <span class="prop-val">${node.properties[k]}</span>
                    </div>
                `;
            });

            pane.innerHTML = `
                <h2>🔍 Selection Detail</h2>
                <div class="detail-card">
                    <div class="detail-header">
                        <h3>Node properties</h3>
                        <div>${labelBadges}</div>
                    </div>
                    <div class="prop-row">
                        <span class="prop-key">internal_id</span>
                        <span class="prop-val">${node.id}</span>
                    </div>
                    ${propsHtml}
                </div>
            `;
        }

        function showEdgeDetails(edge) {
            const pane = document.getElementById("detail-pane");
            
            let propsHtml = "";
            Object.keys(edge.properties).forEach(k => {
                propsHtml += `
                    <div class="prop-row">
                        <span class="prop-key">${k}</span>
                        <span class="prop-val">${edge.properties[k]}</span>
                    </div>
                `;
            });

            pane.innerHTML = `
                <h2>🔍 Selection Detail</h2>
                <div class="detail-card">
                    <div class="detail-header">
                        <h3>Relationship Property</h3>
                        <span class="label-badge">${edge.type}</span>
                    </div>
                    <div class="prop-row">
                        <span class="prop-key">Source ID</span>
                        <span class="prop-val">${edge.source}</span>
                    </div>
                    <div class="prop-row">
                        <span class="prop-key">Target ID</span>
                        <span class="prop-val">${edge.target}</span>
                    </div>
                    ${propsHtml}
                </div>
            `;
        }

        function resetDetailPane() {
            document.getElementById("detail-pane").innerHTML = `
                <h2>🔍 Selection Detail</h2>
                <p class="placeholder">Click on a node or edge to inspect properties</p>
            `;
        }

        function togglePhysics() {
            if (!network) return;
            physicsEnabled = !physicsEnabled;
            network.setOptions({ physics: { enabled: physicsEnabled } });
            
            const btn = document.getElementById("physics-btn");
            if (physicsEnabled) {
                btn.innerText = "Pause Physics";
                btn.classList.remove("btn-secondary");
            } else {
                btn.innerText = "Resume Physics";
                btn.classList.add("btn-secondary");
            }
        }

        function fitNetwork() {
            if (network) {
                network.fit({ animation: { duration: 500, easingFunction: "easeOutQuad" } });
            }
        }

        // Initialize first graph
        loadSelectedGraph();
    </script>
</body>
</html>
"""
    
    # Replace data template
    html_content = html_template.replace("{{DATA}}", json.dumps(all_graph_data))
    
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"\n🎉 Successfully compiled graph data!")
    print(f"🖥️  Visualization file written to: {output_html_path}")
    print(f"👉 Open this link in your browser to view the interactive graphs:")
    # Clickable link output
    link_path = Path(output_html_path).as_uri()
    print(f"   {link_path}")


if __name__ == "__main__":
    main()
