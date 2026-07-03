import sys
import argparse
import asyncio
import time
import httpx
from typing import List, Dict, Any

# Ensure parent path is in sys.path to run from CLI
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from Config.config import START_API_HOST, START_API_PORT
from backend.api import typesense_client

API_URL = f"http://{START_API_HOST}:{START_API_PORT}"

# --- Default Sample Data ---

SAMPLE_EGO_QUADS = [
    {"subject": "IntegratorAgent", "predicate": "hasType", "object": "AI_Agent", "context": "system_architecture"},
    {"subject": "IntegratorAgent", "predicate": "accesses", "object": "working_memory", "context": "cognitive_architecture"},
    {"subject": "IntegratorAgent", "predicate": "accesses", "object": "ego", "context": "cognitive_architecture"},
    {"subject": "EgoMemory", "predicate": "stores", "object": "persistent_knowledge", "context": "ontology"},
    {"subject": "UserProfile", "predicate": "prefersLanguage", "object": "Turkish", "context": "preferences"},
    {"subject": "UserProfile", "predicate": "hasName", "object": "Alice", "context": "identity"}
]

SAMPLE_WORKING_MEMORY_QUADS = [
    {"subject": "CurrentSession", "predicate": "isAbout", "object": "FastAPI_Typesense_Integration", "context": "session_state"},
    {"subject": "UserRequest", "predicate": "demands", "object": "segmented_storage_visualizer", "context": "current_task"},
    {"subject": "Typesense", "predicate": "status", "object": "indexing_active", "context": "infrastructure"}
]

SAMPLE_SHORT_TERM_MEMORIES = [
    {"key": "init_prompt", "content": "How can I check the state of my segmented memory?", "role": "user"},
    {"key": "system_routing", "content": "Routing request to IntegratorAgent. Reading Working Memory and Ego.", "role": "system"},
    {"key": "agent_response", "content": "I have retrieved your persistent settings (Ego) and current context (Working Memory). You can use the visualization script to print them.", "role": "assistant"}
]

# --- Direct Typesense Actions ---

async def direct_clear_session(session_id: str):
    print(f"[Direct] Clearing all segments for session '{session_id}'...")
    for coll in ["session_ego", "session_working_memory", "session_short_term_memory"]:
        try:
            res = await typesense_client.delete_documents_by_query(coll, f"session_id:={session_id}")
            print(f"  - Cleared {res.get('num_deleted', 0)} documents from '{coll}'")
        except Exception as e:
            print(f"  - Error clearing '{coll}': {e}")

async def direct_insert_sample_data(session_id: str):
    print(f"[Direct] Ingesting sample data into session '{session_id}'...")
    t_now = int(time.time())
    
    # 1. Ego Quads
    ego_docs = []
    for item in SAMPLE_EGO_QUADS:
        item_doc = {
            "id": f"ego-{session_id}-{item['subject']}-{item['predicate']}",
            "session_id": session_id,
            "subject": item["subject"],
            "predicate": item["predicate"],
            "object": item["object"],
            "context": item["context"],
            "semantic_text": f"{item['subject']} {item['predicate']} {item['object']}",
            "timestamp": t_now
        }
        ego_docs.append(item_doc)
    try:
        await typesense_client.bulk_index_documents("session_ego", ego_docs)
        print(f"  - Imported {len(ego_docs)} quads into Ego")
    except Exception as e:
        print(f"  - Error importing Ego quads: {e}")

    # 2. Working Memory Quads
    wm_docs = []
    for item in SAMPLE_WORKING_MEMORY_QUADS:
        item_doc = {
            "id": f"wm-{session_id}-{item['subject']}-{item['predicate']}",
            "session_id": session_id,
            "subject": item["subject"],
            "predicate": item["predicate"],
            "object": item["object"],
            "context": item["context"],
            "semantic_text": f"{item['subject']} {item['predicate']} {item['object']}",
            "timestamp": t_now
        }
        wm_docs.append(item_doc)
    try:
        await typesense_client.bulk_index_documents("session_working_memory", wm_docs)
        print(f"  - Imported {len(wm_docs)} quads into Working Memory")
    except Exception as e:
        print(f"  - Error importing Working Memory quads: {e}")

    # 3. Short Term Memory
    stm_docs = []
    for item in SAMPLE_SHORT_TERM_MEMORIES:
        item_doc = {
            "id": f"stm-{session_id}-{item['key']}",
            "session_id": session_id,
            "key": item["key"],
            "content": item["content"],
            "role": item["role"],
            "timestamp": t_now
        }
        stm_docs.append(item_doc)
    try:
        await typesense_client.bulk_index_documents("session_short_term_memory", stm_docs)
        print(f"  - Imported {len(stm_docs)} memories into Short-Term Memory")
    except Exception as e:
        print(f"  - Error importing Short-Term memories: {e}")

async def direct_fetch_data(session_id: str) -> Dict[str, List[Dict[str, Any]]]:
    data = {}
    for coll in ["session_ego", "session_working_memory", "session_short_term_memory"]:
        try:
            res = await typesense_client.search_collection(coll, {
                "q": "*",
                "filter_by": f"session_id:={session_id}",
                "sort_by": "timestamp:asc",
                "per_page": 100
            })
            data[coll] = [hit["document"] for hit in res.get("hits", [])]
        except Exception as e:
            print(f"[Warning] Error fetching from '{coll}': {e}")
            data[coll] = []
    return data

# --- FastAPI HTTP Actions ---

def api_clear_session(session_id: str):
    print(f"[API] Clearing all segments for session '{session_id}' via HTTP...")
    for path in ["ego", "working-memory", "short-term-memory"]:
        try:
            res = httpx.delete(f"{API_URL}/api/session/{session_id}/{path}", timeout=10.0)
            if res.status_code == 200:
                print(f"  - Cleared segment '{path}': {res.json().get('deleted_count', 0)} deleted")
            else:
                print(f"  - Failed to clear segment '{path}': {res.status_code} - {res.text}")
        except Exception as e:
            print(f"  - Connection error clearing '{path}': {e}")

def api_insert_sample_data(session_id: str):
    print(f"[API] Ingesting sample data into session '{session_id}' via HTTP...")
    
    # 1. Ego Quads
    try:
        res = httpx.post(f"{API_URL}/api/session/{session_id}/ego/bulk", json=SAMPLE_EGO_QUADS, timeout=10.0)
        if res.status_code == 201:
            print(f"  - Ingested {len(res.json())} quads into Ego")
        else:
            print(f"  - Failed to ingest Ego: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"  - Connection error on Ego: {e}")

    # 2. Working Memory Quads
    try:
        res = httpx.post(f"{API_URL}/api/session/{session_id}/working-memory/bulk", json=SAMPLE_WORKING_MEMORY_QUADS, timeout=10.0)
        if res.status_code == 201:
            print(f"  - Ingested {len(res.json())} quads into Working Memory")
        else:
            print(f"  - Failed to ingest Working Memory: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"  - Connection error on Working Memory: {e}")

    # 3. Short Term Memory
    try:
        res = httpx.post(f"{API_URL}/api/session/{session_id}/short-term-memory/bulk", json=SAMPLE_SHORT_TERM_MEMORIES, timeout=10.0)
        if res.status_code == 201:
            print(f"  - Ingested {len(res.json())} memories into Short-Term Memory")
        else:
            print(f"  - Failed to ingest Short-Term Memory: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"  - Connection error on Short-Term Memory: {e}")

def api_fetch_data(session_id: str) -> Dict[str, List[Dict[str, Any]]]:
    data = {}
    # Ego
    try:
        res = httpx.get(f"{API_URL}/api/session/{session_id}/ego", params={"limit": 100}, timeout=10.0)
        data["session_ego"] = res.json() if res.status_code == 200 else []
    except Exception as e:
        print(f"[Warning] Connection error fetching Ego: {e}")
        data["session_ego"] = []

    # Working Memory
    try:
        res = httpx.get(f"{API_URL}/api/session/{session_id}/working-memory", params={"limit": 100}, timeout=10.0)
        data["session_working_memory"] = res.json() if res.status_code == 200 else []
    except Exception as e:
        print(f"[Warning] Connection error fetching Working Memory: {e}")
        data["session_working_memory"] = []

    # Short Term Memory
    try:
        res = httpx.get(f"{API_URL}/api/session/{session_id}/short-term-memory", params={"limit": 100}, timeout=10.0)
        data["session_short_term_memory"] = res.json() if res.status_code == 200 else []
    except Exception as e:
        print(f"[Warning] Connection error fetching Short Term Memory: {e}")
        data["session_short_term_memory"] = []

    return data

# --- Formatting & Output ---

def print_quads(title: str, quads: List[Dict[str, Any]]):
    print("\n" + "=" * 120)
    print(f"{title} ({len(quads)} Triples)")
    print("=" * 120)
    if not quads:
        print("  (Empty)")
        return
        
    print(f"{'SUBJECT':<18} | {'PREDICATE':<15} | {'OBJECT':<18} | {'CONTEXT':<18} | {'EMBEDDING (FIRST 3 + DIM)'}")
    print("-" * 120)
    for q in quads:
        sub = q.get("subject", "")
        pred = q.get("predicate", "")
        obj = q.get("object", "")
        ctx = q.get("context", "") or "None"
        emb = q.get("embedding")
        emb_str = "None"
        if isinstance(emb, list) and len(emb) > 0:
            emb_str = f"[{', '.join(f'{x:.4f}' for x in emb[:3])}, ...] ({len(emb)} dim)"
        print(f"{sub:<18} | {pred:<15} | {obj:<18} | {ctx:<18} | {emb_str}")

def print_transcript(title: str, memories: List[Dict[str, Any]]):
    print("\n" + "=" * 120)
    print(f"{title} ({len(memories)} Turns)")
    print("=" * 120)
    if not memories:
        print("  (Empty)")
        return
        
    for m in memories:
        role = m.get("role", "unknown").upper()
        content = m.get("content", "")
        key = m.get("key", "")
        emb = m.get("embedding")
        emb_str = "None"
        if isinstance(emb, list) and len(emb) > 0:
            emb_str = f"[{', '.join(f'{x:.4f}' for x in emb[:3])}, ...] ({len(emb)} dim)"
        
        prefix = f"[{role}]"
        key_str = f" ({key})" if key else ""
        print(f"{prefix}{key_str}: {content}")
        print(f"  +- Vector Embedding: {emb_str}")
        print("-" * 120)

# --- Main Program Execution ---

async def main():
    parser = argparse.ArgumentParser(
        description="Insert sample data and visualize Typesense segmented session storage."
    )
    parser.add_argument(
        "--session-id",
        type=str,
        default="test-session-123",
        help="The session identifier to use/visualize (default: test-session-123)"
    )
    parser.add_argument(
        "--insert",
        action="store_true",
        help="Insert default sample memory data into the session before visualizing"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all segments for this session before inserting/visualizing"
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Connect directly to Typesense, bypassing the FastAPI server"
    )
    
    args = parser.parse_args()
    session_id = args.session_id
    
    # 1. Determine connection method
    use_api = not args.direct
    if use_api:
        # Check if API server is reachable
        try:
            res = httpx.get(f"{API_URL}/health", timeout=2.0)
            if res.status_code != 200 or res.json().get("status") != "ok":
                print("[Warning] FastAPI health check failed. Falling back to direct Typesense access.")
                use_api = False
        except Exception:
            print("[Warning] FastAPI server is not running or unreachable. Falling back to direct Typesense access.")
            use_api = False
            
    print(f"Operating Mode: {'[FastAPI Server]' if use_api else '[Direct Typesense Database]'}")
    
    # Ensure Typesense collections exist before performing database operations in direct mode
    if not use_api:
        print("Checking/Initializing Typesense collections...")
        await typesense_client.init_typesense_collections()
        
    # 2. Perform Clear Action
    if args.clear:
        if use_api:
            api_clear_session(session_id)
        else:
            await direct_clear_session(session_id)
            
    # 3. Perform Insert Action
    if args.insert:
        if use_api:
            api_insert_sample_data(session_id)
        else:
            await direct_insert_sample_data(session_id)
            
    # 4. Fetch and Visualize
    print(f"\nRetrieving segmented session memory for '{session_id}'...")
    if use_api:
        data = api_fetch_data(session_id)
    else:
        data = await direct_fetch_data(session_id)
        
    # Visualize segments
    print_quads("PERSISTENT FACT SEGMENT (EGO)", data.get("session_ego", []))
    print_quads("CURRENT WORKING CONTEXT (WORKING MEMORY)", data.get("session_working_memory", []))
    print_transcript("CONVERSATION TRANSCRIPT (SHORT-TERM MEMORY)", data.get("session_short_term_memory", []))
    print("\n" + "=" * 80)

if __name__ == "__main__":
    # Standard check to handle windows event loop policy
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
