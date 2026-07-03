# -*- coding: utf-8 -*-
"""Extracts the Leiden hierarchy and PPMI graph directly from SQLite and generates an interactive HTML visualizer."""

import json
import sqlite3
import os
import sys
from pathlib import Path

# Add backend directory to Python path if running script directly
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from Config.config import LEMMA_MATRIX_DATABASE_PATH

def fetch_sqlite_graph():
    """Extract all nodes and edges from lemma_matrix.db."""
    conn = sqlite3.connect(LEMMA_MATRIX_DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    nodes = []
    edges = []
    
    try:
        # 1. Keywords (Level 0)
        cur.execute("""
            SELECT v.id as vocab_id, v.word, c.id as concept_id, c.parent_id, c.pagerank_score, c.is_leader
            FROM vocabulary v
            LEFT JOIN concepts c ON v.id = c.vocab_id AND c.level = 0
        """)
        for r in cur.fetchall():
            nodes.append({
                "id": f"v_{r['vocab_id']}",
                "labels": ["Keyword"],
                "properties": {
                    "word": r["word"],
                    "vocab_id": r["vocab_id"],
                    "concept_id": r["concept_id"],
                    "parent_id": r["parent_id"],
                    "pagerank": float(r["pagerank_score"] or 1.0),
                    "is_leader": bool(r["is_leader"])
                }
            })
            # Add CHILD_OF edge to parent concept if exists
            if r["parent_id"] is not None:
                edges.append({
                    "source": f"v_{r['vocab_id']}",
                    "target": f"c_{r['parent_id']}",
                    "type": "CHILD_OF",
                    "properties": {}
                })
                
        # 2. Concepts (Level > 0)
        cur.execute("SELECT id, level, label, parent_id, pagerank_score, is_leader FROM concepts WHERE level > 0")
        for r in cur.fetchall():
            nodes.append({
                "id": f"c_{r['id']}",
                "labels": ["Concept"],
                "properties": {
                    "label": r["label"],
                    "concept_id": r["id"],
                    "level": r["level"],
                    "parent_id": r["parent_id"],
                    "pagerank": float(r["pagerank_score"] or 1.0),
                    "is_leader": bool(r["is_leader"])
                }
            })
            if r["parent_id"] is not None:
                edges.append({
                    "source": f"c_{r['id']}",
                    "target": f"c_{r['parent_id']}",
                    "type": "CHILD_OF",
                    "properties": {}
                })

        # 3. PPMI Edges
        cur.execute("SELECT vocab1_id, vocab2_id, weight FROM ppmi_lemma_matrix")
        for r in cur.fetchall():
            edges.append({
                "source": f"v_{r['vocab1_id']}",
                "target": f"v_{r['vocab2_id']}",
                "type": "CO_OCCUR_WITH",
                "properties": {"weight": float(r["weight"])}
            })
            
        # 4. Concept Connections
        cur.execute("SELECT node1_id, node2_id, weight FROM concept_connections")
        for r in cur.fetchall():
            edges.append({
                "source": f"c_{r['node1_id']}",
                "target": f"c_{r['node2_id']}",
                "type": "CONCEPT_CONNECTION",
                "properties": {"weight": float(r["weight"])}
            })
            
    except Exception as e:
        print(f"⚠️ Error reading SQLite DB: {e}")
        
    finally:
        conn.close()
        
    return {"nodes": nodes, "edges": edges}


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SQLite Graph Visualization</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; background-color: #0f172a; color: #f1f5f9; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
        header { background-color: #1e293b; border-bottom: 1px solid #334155; padding: 15px 25px; display: flex; justify-content: space-between; align-items: center; z-index: 10; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        .header-title h1 { font-size: 1.4rem; font-weight: 700; background: linear-gradient(135deg, #06b6d4, #f59e0b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header-title p { font-size: 0.8rem; color: #94a3b8; margin-top: 2px; }
        .app-container { flex: 1; display: flex; position: relative; height: calc(100vh - 75px); }
        #network-container { flex: 1; height: 100%; background-color: #090d16; }
        .sidebar { width: 360px; background-color: #1e293b; border-left: 1px solid #334155; display: flex; flex-direction: column; height: 100%; z-index: 5; box-shadow: -4px 0 10px -3px rgba(0,0,0,0.2); }
        .sidebar-section { padding: 20px; border-bottom: 1px solid #334155; }
        .sidebar-section h2 { font-size: 1.1rem; font-weight: 600; color: #cbd5e1; margin-bottom: 15px; }
        .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .meta-card { background-color: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 12px; text-align: center; }
        .meta-card .num { font-size: 1.6rem; font-weight: 700; color: #06b6d4; }
        .meta-card .label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; margin-top: 4px; }
        .properties-detail { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; }
        .properties-detail h2 { font-size: 1.1rem; font-weight: 600; color: #cbd5e1; margin-bottom: 15px; }
        .properties-detail p.placeholder { color: #64748b; font-style: italic; text-align: center; margin-top: 40px; }
        .detail-card { background-color: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 15px; margin-bottom: 15px; transition: border-color 0.2s; }
        .detail-card:hover { border-color: #475569; }
        .detail-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #334155; padding-bottom: 8px; }
        .detail-header h3 { font-size: 0.95rem; color: #06b6d4; }
        .label-badge { border: 1px solid #475569; font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; font-weight: bold; }
        .label-badge-keyword { background-color: rgba(6, 182, 212, 0.15); border-color: #06b6d4; color: #22d3ee; }
        .label-badge-concept { background-color: rgba(245, 158, 11, 0.15); border-color: #f59e0b; color: #fbbf24; }
        .prop-row { display: flex; flex-direction: column; gap: 4px; margin-bottom: 10px; }
        .prop-key { font-size: 0.75rem; color: #64748b; font-weight: 600; text-transform: uppercase; }
        .prop-val { font-size: 0.85rem; color: #e2e8f0; word-break: break-all; background-color: #1e293b; padding: 6px 8px; border-radius: 4px; font-family: monospace; }
        .controls-panel { position: absolute; bottom: 20px; left: 20px; background-color: rgba(30,41,59,0.85); backdrop-filter: blur(8px); border: 1px solid #334155; border-radius: 8px; padding: 12px; display: flex; gap: 10px; z-index: 10; }
        .btn { background-color: #06b6d4; color: #0f172a; border: none; border-radius: 4px; padding: 6px 12px; font-size: 0.8rem; font-weight: 700; cursor: pointer; transition: background-color 0.2s; }
        .btn:hover { background-color: #22d3ee; }
        .btn-secondary { background-color: #475569; color: #f1f5f9; }
        .btn-secondary:hover { background-color: #334155; }
        
        /* Result Item styling */
        .result-item {
            padding: 10px;
            background-color: #0f172a;
            border: 1px solid #334155;
            border-radius: 6px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .result-item:hover {
            border-color: #06b6d4;
            background-color: #1e293b;
        }

        /* Tabs Styling */
        .tab-bar {
            display: flex;
            background-color: #0f172a;
            border-bottom: 1px solid #334155;
        }
        .tab-btn {
            flex: 1;
            padding: 14px 10px;
            background: none;
            border: none;
            color: #64748b;
            font-size: 0.8rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s ease;
            text-align: center;
            border-bottom: 2px solid transparent;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .tab-btn:hover {
            color: #cbd5e1;
            background-color: rgba(255,255,255,0.02);
        }
        .tab-btn.active {
            color: #06b6d4;
            border-bottom-color: #06b6d4;
            background-color: rgba(6, 182, 212, 0.05);
        }
        .tab-content {
            display: none;
            flex-direction: column;
            flex: 1;
            overflow-y: auto;
            height: calc(100% - 50px);
        }
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <h1>SQLite Hierarchical Graph Explorer</h1>
            <p>Color-Blind Accessible Interactive Spreading Activation</p>
        </div>
    </header>

    <div class="app-container">
        <div id="network-container"></div>
        <div class="controls-panel">
            <button class="btn" id="physics-btn" onclick="togglePhysics()">Pause Physics</button>
            <button class="btn btn-secondary" onclick="fitNetwork()">Zoom Fit</button>
        </div>
        <div class="sidebar">
            <div class="tab-bar">
                <button class="tab-btn active" id="btn-config" onclick="switchTab('tab-config')">⚙️ Config</button>
                <button class="tab-btn" id="btn-details" onclick="switchTab('tab-details')">🔍 Details</button>
                <button class="tab-btn" id="btn-results" onclick="switchTab('tab-results')">🔥 Results</button>
            </div>

            <!-- Tab 1: Config -->
            <div id="tab-config" class="tab-content" style="display: flex;">
                <div class="sidebar-section">
                    <h2>📊 Graph Info</h2>
                    <div class="meta-grid">
                        <div class="meta-card"><div class="num" id="node-count">0</div><div class="label">Nodes</div></div>
                        <div class="meta-card"><div class="num" id="edge-count">0</div><div class="label">Edges</div></div>
                    </div>
                </div>
                <div class="sidebar-section" style="border-bottom: 1px solid #334155; padding-bottom: 15px;">
                    <h2>⚙️ Spreading Settings</h2>
                    <div style="display: flex; flex-direction: column; gap: 10px;">
                        <div>
                            <label style="font-size: 0.8rem; color: #cbd5e1; display: flex; justify-content: space-between;">
                                <span>Steps (Propagation Depth):</span>
                                <span id="steps-val" style="color: #06b6d4; font-weight: bold;">3</span>
                            </label>
                            <input type="range" id="steps-input" min="1" max="8" value="3" style="width: 100%; accent-color: #06b6d4;" oninput="document.getElementById('steps-val').innerText=this.value">
                        </div>
                        <div>
                            <label style="font-size: 0.8rem; color: #cbd5e1; display: flex; justify-content: space-between;">
                                <span>Decay Factor:</span>
                                <span id="decay-val" style="color: #06b6d4; font-weight: bold;">0.5</span>
                            </label>
                            <input type="range" id="decay-input" min="0.1" max="1.0" step="0.05" value="0.5" style="width: 100%; accent-color: #06b6d4;" oninput="document.getElementById('decay-val').innerText=this.value">
                        </div>
                        <div>
                            <label style="font-size: 0.8rem; color: #cbd5e1; display: flex; justify-content: space-between;">
                                <span>Min Threshold:</span>
                                <span id="threshold-val" style="color: #06b6d4; font-weight: bold;">0.05</span>
                            </label>
                            <input type="range" id="threshold-input" min="0.01" max="0.5" step="0.01" value="0.05" style="width: 100%; accent-color: #06b6d4;" oninput="document.getElementById('threshold-val').innerText=this.value">
                        </div>
                        <div>
                            <label style="font-size: 0.8rem; color: #cbd5e1; display: flex; justify-content: space-between;">
                                <span>Max Result Cap (Top K):</span>
                                <span id="topk-val" style="color: #06b6d4; font-weight: bold;">50</span>
                            </label>
                            <input type="range" id="topk-input" min="10" max="300" step="10" value="50" style="width: 100%; accent-color: #06b6d4;" oninput="document.getElementById('topk-val').innerText=this.value">
                        </div>
                    </div>
                </div>
            </div>

            <!-- Tab 2: Selection Detail -->
            <div id="tab-details" class="tab-content">
                <div class="properties-detail" id="detail-pane">
                    <h2>🔍 Selection Detail</h2>
                    <p class="placeholder">Click on a node to inspect & spread activation</p>
                </div>
            </div>

            <!-- Tab 3: Spreading Results -->
            <div id="tab-results" class="tab-content">
                <div class="properties-detail" id="results-pane">
                    <h2>🔥 Spreading Results</h2>
                    <p class="placeholder">No activation run yet</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        const rawData = {{DATA}};
        const graph = rawData["lemma_matrix.db"];
        let network = null;
        let physicsEnabled = true;

        // Color-blind friendly scheme: High-contrast Cyan and Amber/Yellow
        const COLORS = {
            Keyword: { background: "#06b6d4", border: "#0891b2", highlight: { background: "#22d3ee", border: "#06b6d4" } },
            Concept: { background: "#f59e0b", border: "#d97706", highlight: { background: "#fbbf24", border: "#f59e0b" } },
            default: { background: "#64748b", border: "#475569", highlight: { background: "#94a3b8", border: "#64748b" } }
        };

        function switchTab(tabId) {
            document.querySelectorAll(".tab-content").forEach(el => {
                el.style.display = "none";
            });
            const target = document.getElementById(tabId);
            if (target) {
                target.style.display = "flex";
            }
            document.querySelectorAll(".tab-btn").forEach(btn => {
                btn.classList.remove("active");
            });
            const activeBtn = document.getElementById("btn-" + tabId.replace("tab-", ""));
            if (activeBtn) activeBtn.classList.add("active");
        }

        function resetResultsPane() {
            const resultsPane = document.getElementById("results-pane");
            resultsPane.innerHTML = `
                <h2>🔥 Spreading Results</h2>
                <p class="placeholder">No activation run yet</p>
            `;
            // Switch to Config tab
            switchTab("tab-config");
        }

        function focusOnNode(nodeId) {
            if (network) {
                network.selectNodes([nodeId]);
                network.focus(nodeId, {
                    scale: 1.2,
                    animation: { duration: 500, easingFunction: "easeOutQuad" }
                });
                const nodeObj = graph.nodes.find(n => n.id === nodeId);
                if (nodeObj) {
                    showNodeDetails(nodeObj);
                }
            }
        }

        function loadGraph() {
            document.getElementById("node-count").innerText = graph.nodes.length;
            document.getElementById("edge-count").innerText = graph.edges.length;
            resetResultsPane();
            
            const visNodes = graph.nodes.map(n => {
                const labelType = n.labels[0] || "default";
                const palette = COLORS[labelType] || COLORS.default;
                let displayLabel = n.properties.word || n.properties.label || `Node ${n.id}`;
                
                // Indicate level in title
                let title = `Type: ${labelType}`;
                if (n.properties.level !== undefined) title += `\\nLevel: ${n.properties.level}`;
                if (n.properties.pagerank !== undefined) title += `\\nPageRank: ${n.properties.pagerank.toFixed(3)}`;
                
                return {
                    id: n.id,
                    label: displayLabel,
                    title: title,
                    color: palette,
                    // Visual Shape cue distinction: Concept = hexagon, Keyword = circular dot
                    shape: labelType === "Concept" ? "hexagon" : "dot",
                    size: labelType === "Concept" ? 24 : 16,
                    font: { color: "#f1f5f9", size: 12 },
                    rawData: n
                };
            });

            const visEdges = graph.edges.map((e, idx) => {
                let weight = e.properties.weight ? parseFloat(e.properties.weight) : 1.0;
                let displayLabel = e.type === "CHILD_OF" ? "" : weight.toFixed(2);
                
                return {
                    id: `edge_${idx}`,
                    from: e.source,
                    to: e.target,
                    label: displayLabel,
                    title: `Type: ${e.type}\\nWeight: ${weight}`,
                    arrows: e.type === "CHILD_OF" ? "to" : "",
                    width: Math.min(Math.max(weight * 1.5, 1), 6),
                    color: { color: "#475569", highlight: "#06b6d4", hover: "#22d3ee" },
                    font: { color: "#94a3b8", size: 10, align: "horizontal" },
                    rawData: e
                };
            });

            const container = document.getElementById("network-container");
            const data = { nodes: new vis.DataSet(visNodes), edges: new vis.DataSet(visEdges) };
            
            const options = {
                nodes: { borderWidth: 2 },
                edges: { smooth: { type: "continuous", roundness: 0.5 } },
                physics: {
                    barnesHut: { gravitationalConstant: -3000, centralGravity: 0.3, springLength: 120 }
                },
                interaction: { hover: true }
            };

            network = new vis.Network(container, data, options);
            
            network.on("click", function (params) {
                if (params.nodes.length > 0) {
                    const nodeData = data.nodes.get(params.nodes[0]);
                    showNodeDetails(nodeData.rawData);
                }
            });
        }

        function showNodeDetails(node) {
            const pane = document.getElementById("detail-pane");
            let propsHtml = "";
            Object.keys(node.properties).forEach(k => {
                propsHtml += `<div class="prop-row"><span class="prop-key">${k}</span><span class="prop-val">${node.properties[k]}</span></div>`;
            });

            const badgeClass = node.labels[0] === "Concept" ? "label-badge-concept" : "label-badge-keyword";

            pane.innerHTML = `
                <h2>🔍 Selection Detail</h2>
                <div class="detail-card">
                    <div class="detail-header">
                        <h3>Node properties</h3>
                        <span class="label-badge ${badgeClass}">${node.labels[0]}</span>
                    </div>
                    ${propsHtml}
                    <button class="btn" style="margin-top: 15px; width: 100%; background-color: #8b5cf6; color: #ffffff;" onclick="simulateSpreadingActivation('${node.id}')">
                        🔥 Spread Activation
                    </button>
                    <button class="btn btn-secondary" style="margin-top: 5px; width: 100%;" onclick="loadGraph()">
                        Reset Graph
                    </button>
                </div>
            `;
        }

        function simulateSpreadingActivation(seedId) {
            const decay = parseFloat(document.getElementById("decay-input").value);
            const threshold = parseFloat(document.getElementById("threshold-input").value);
            const maxSteps = parseInt(document.getElementById("steps-input").value);
            const topK = parseInt(document.getElementById("topk-input").value);
            const hierarchyWeight = 1.0;
            
            let adjacency = {};
            graph.edges.forEach(e => {
                if (!adjacency[e.source]) adjacency[e.source] = [];
                if (!adjacency[e.target]) adjacency[e.target] = [];
                
                let weight = 1.0;
                if (e.type === "CO_OCCUR_WITH" || e.type === "CONCEPT_CONNECTION") {
                    weight = parseFloat(e.properties.weight || 1.0);
                } else if (e.type === "CHILD_OF") {
                    let childNode = graph.nodes.find(n => n.id === e.source);
                    let pr = (childNode && childNode.properties.pagerank) ? parseFloat(childNode.properties.pagerank) : 1.0;
                    weight = hierarchyWeight * pr;
                }
                
                adjacency[e.source].push({target: e.target, weight: weight});
                adjacency[e.target].push({target: e.source, weight: weight});
            });

            let currentActivations = {};
            currentActivations[seedId] = 1.0;

            for (let step = 0; step < maxSteps; step++) {
                let nextActivations = {};
                
                for (let node in currentActivations) {
                    let energy = currentActivations[node];
                    if (energy < threshold) continue;
                    
                    // Energy stays at node (decayed)
                    let currentNext = nextActivations[node] || 0.0;
                    nextActivations[node] = Math.max(currentNext, energy * decay);
                    
                    // Spread to neighbors
                    let nbs = adjacency[node] || [];
                    nbs.forEach(nb => {
                        let scaledWeight = Math.log1p(nb.weight); // log(1 + weight)
                        let energyTransfer = energy * scaledWeight * decay;
                        
                        let currentNbEnergy = nextActivations[nb.target] || 0.0;
                        let newEnergy = Math.min(1.0, currentNbEnergy + energyTransfer);
                        nextActivations[nb.target] = newEnergy;
                    });
                }
                currentActivations = nextActivations;
                currentActivations[seedId] = 1.0; // Seed stays active
            }

            // Populate tabular Results sidebar with sorting and Top K filter
            let sortedResults = Object.keys(currentActivations)
                .map(nodeId => {
                    let nodeObj = graph.nodes.find(n => n.id === nodeId);
                    return {
                        id: nodeId,
                        label: nodeObj ? (nodeObj.properties.word || nodeObj.properties.label) : nodeId,
                        type: nodeObj ? nodeObj.labels[0] : "Unknown",
                        activation: currentActivations[nodeId]
                    };
                })
                .filter(res => res.activation > threshold)
                .sort((a, b) => b.activation - a.activation);

            // Slice to topK limit
            if (topK && sortedResults.length > topK) {
                sortedResults = sortedResults.slice(0, topK);
            }

            const allowedActiveIds = new Set(sortedResults.map(r => r.id));

            // High contrast, color-blind friendly highlights:
            // - Seed is vibrant Violet/Purple
            // - Activated nodes have extremely thick Electric Yellow/White borders
            // - Sizes are dynamically boosted to give visual size cues
            let updateNodes = [];
            network.body.data.nodes.forEach(node => {
                let act = currentActivations[node.id] || 0;
                
                // Only highlight if node is inside the allowed topK active set
                if (act > threshold && allowedActiveIds.has(node.id)) {
                    let intensity = Math.min(1.0, act); // cap at 1.0
                    let baseSize = node.rawData.labels[0] === "Concept" ? 24 : 16;
                    let sizeBoost = baseSize + (intensity * 14); // Double size cue
                    
                    let isSeed = node.id === seedId;
                    let bgColor = isSeed ? "#8b5cf6" : undefined; // Violet seed
                    let borderColor = isSeed ? "#ffffff" : "#facc15"; // Gold border for activated nodes
                    
                    updateNodes.push({
                        id: node.id,
                        size: sizeBoost,
                        borderWidth: 3 + (intensity * 5),
                        color: { border: borderColor, background: bgColor },
                        title: node.title + "\\n[+] Activation: " + act.toFixed(4)
                    });
                } else {
                    // Reset styling for nodes that did not make the topK cut
                    let baseSize = node.rawData.labels[0] === "Concept" ? 24 : 16;
                    const palette = COLORS[node.rawData.labels[0] || "default"] || COLORS.default;
                    updateNodes.push({
                        id: node.id,
                        size: baseSize,
                        borderWidth: 2,
                        color: palette,
                        title: node.title
                    });
                }
            });
            network.body.data.nodes.update(updateNodes);

            let resultsPane = document.getElementById("results-pane");
            let listHtml = sortedResults.map((res, index) => {
                let badgeClass = res.type === "Keyword" ? "label-badge-keyword" : "label-badge-concept";
                let isSeed = res.id === seedId;
                let cardStyle = isSeed 
                    ? "border-left: 4px solid #8b5cf6; background-color: rgba(139, 92, 246, 0.05);" 
                    : "border-left: 4px solid #facc15;";
                
                return `
                    <div class="result-item" style="${cardStyle}" onclick="focusOnNode('${res.id}')">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <strong style="color: #f1f5f9; font-size: 0.9rem;">#${index+1} ${res.label}</strong>
                            <span class="label-badge ${badgeClass}">${res.type}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.75rem; margin-top: 4px; color: #94a3b8;">
                            <span>Activation: <strong>${res.activation.toFixed(4)}</strong></span>
                            ${isSeed ? '<span style="color: #c084fc; font-weight: bold;">[SEED]</span>' : ''}
                        </div>
                    </div>
                `;
            }).join("");

            let seedNodeObj = graph.nodes.find(n => n.id === seedId);
            let seedLabel = seedNodeObj ? (seedNodeObj.properties.word || seedNodeObj.properties.label) : seedId;

            resultsPane.innerHTML = `
                <h2>🔥 Spreading Results</h2>
                <div style="margin-bottom: 12px; font-size: 0.8rem; color: #94a3b8; border-bottom: 1px solid #334155; padding-bottom: 8px;">
                    Seed: <strong style="color: #c084fc;">${seedLabel}</strong> | Active: <strong>${sortedResults.length}</strong>
                </div>
                <div style="flex: 1; overflow-y: auto; padding-right: 4px;">
                    ${listHtml}
                </div>
            `;
            
            // Auto switch to Results tab
            switchTab("tab-results");
        }

        function togglePhysics() {
            physicsEnabled = !physicsEnabled;
            network.setOptions({ physics: { enabled: physicsEnabled } });
            document.getElementById("physics-btn").innerText = physicsEnabled ? "Pause Physics" : "Resume Physics";
        }
        function fitNetwork() { network.fit(); }

        loadGraph();
    </script>
</body>
</html>
"""

def main():
    print("[INFO] Extracting full graph directly from SQLite...")
    graph_data = fetch_sqlite_graph()
    
    num_nodes = len(graph_data["nodes"])
    num_edges = len(graph_data["edges"])
    print(f"   Loaded {num_nodes} nodes and {num_edges} edges.")
    
    if num_nodes == 0:
        print("[WARNING] The lemma_matrix.db is EMPTY.")
        print("   You need to run your data ingest and build_hierarchy.py first to see the graph!")
        
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_html_path = os.path.join(script_dir, "visualize_sqlite.html")
    
    html_content = HTML_TEMPLATE.replace("{{DATA}}", json.dumps({"lemma_matrix.db": graph_data}))
    
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"\n[SUCCESS] Successfully compiled graph data!")
    print(f"[INFO] Visualization file written to: {output_html_path}")
    print(f"Open this link in your browser to view the interactive graphs:")
    print(f"   {Path(output_html_path).as_uri()}")

if __name__ == "__main__":
    main()
