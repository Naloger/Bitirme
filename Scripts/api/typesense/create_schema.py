import sys
import asyncio
from pathlib import Path

# Add project root directory to Python path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

from backend.api import typesense_client

async def main():
    print("Checking Typesense and Ollama connections...")
    try:
        # Check active settings
        print(f"Typesense Endpoint: http://{typesense_client.TYPESENSE_HOST}:{typesense_client.TYPESENSE_PORT}")
        print(f"Embedding Provider: {typesense_client.TYPESENSE_EMBEDDING_PROVIDER} ({typesense_client.TYPESENSE_EMBEDDING_MODEL})")
        
        # Verify Ollama pulled model if provider is Ollama
        if typesense_client.TYPESENSE_EMBEDDING_PROVIDER == "ollama":
            print("Verifying Ollama embedding model...")
            await typesense_client.ensure_ollama_model_pulled()
            
        print("Ensuring Typesense collection schemas exist...")
        await typesense_client.init_typesense_collections()
        print("Success: All memory schemas have been created or verified successfully!")
        
    except Exception as exc:
        print(f"Error: Failed to create or verify collection schemas: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
