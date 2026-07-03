import sys
import argparse
import asyncio
from pathlib import Path
import httpx

# Add project root directory to Python path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

from backend.api import typesense_client

COLLECTIONS = ["session_ego", "session_working_memory", "session_short_term_memory"]

async def clean_collection(collection: str, session_id: str | None, drop: bool):
    """Cleans or drops a single collection."""
    if drop:
        print(f"Dropping and recreating collection: {collection}...")
        url = f"http://{typesense_client.TYPESENSE_HOST}:{typesense_client.TYPESENSE_PORT}/collections/{collection}"
        headers = {"X-TYPESENSE-API-KEY": typesense_client.TYPESENSE_API_KEY}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Drop collection
                response = await client.delete(url, headers=headers)
                if response.status_code == 200:
                    print(f"Dropped collection '{collection}'.")
                elif response.status_code == 404:
                    print(f"Collection '{collection}' did not exist. Skipping drop.")
                else:
                    print(f"Warning dropping '{collection}': {response.text}")
                    
                # Recreate collection
                await typesense_client.init_typesense_collections()
                print(f"Recreated collection '{collection}' schema.")
            except Exception as e:
                print(f"Error dropping/recreating collection '{collection}': {e}", file=sys.stderr)
    else:
        # Construct filter criteria
        if session_id:
            filter_by = f"session_id:={session_id}"
            desc = f"session ID '{session_id}'"
        else:
            filter_by = "timestamp:>0"
            desc = "all sessions"
            
        print(f"Clearing documents from '{collection}' for {desc}...")
        try:
            res = await typesense_client.delete_documents_by_query(collection, filter_by=filter_by)
            count = res.get("num_deleted", 0)
            print(f"Successfully deleted {count} documents from '{collection}'.")
        except Exception as e:
            # Handle if collection doesn't exist
            if "not found" in str(e).lower() or "404" in str(e):
                print(f"Warning: Collection '{collection}' does not exist. Run 'create_schema.py' first.")
            else:
                print(f"Error cleaning collection '{collection}': {e}", file=sys.stderr)

async def main():
    parser = argparse.ArgumentParser(
        description="Clean or reset Typesense segmented session memory data."
    )
    parser.add_argument(
        "--collection", "-c",
        choices=["all", "ego", "working", "short_term"],
        default="all",
        help="Segmented memory collection to clean (default: all)"
    )
    parser.add_argument(
        "--session-id", "-s",
        help="Clean records matching a specific session ID only. If omitted, cleans all records."
    )
    parser.add_argument(
        "--drop", "-d",
        action="store_true",
        help="Drop and recreate the collection schema structure (restores empty schema). Highly recommended if collections were corrupted."
    )
    
    args = parser.parse_args()
    
    # Resolve selected collections
    if args.collection == "all":
        selected = COLLECTIONS
    elif args.collection == "ego":
        selected = ["session_ego"]
    elif args.collection == "working":
        selected = ["session_working_memory"]
    else:
        selected = ["session_short_term_memory"]
        
    print(f"Starting clean operation (drop={args.drop})...")
    
    for coll in selected:
        await clean_collection(coll, args.session_id, args.drop)
        
    print("Clean operation completed.")

if __name__ == "__main__":
    asyncio.run(main())
