#!/usr/bin/env python3
"""Check Ollama models and endpoint status."""
import urllib.request
from urllib import error
import json
import sys

try:
    print("Checking Ollama endpoint: http://127.0.0.1:11434/api/tags")
    with urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=5) as r:
        data = json.loads(r.read().decode())
        print("\n✓ Ollama is responding")
        print("\nAvailable models:")
        if 'models' in data:
            for model in data['models']:
                name = model.get('name', 'unknown')
                size = model.get('size', 0)
                print(f"  - {name} ({size / 1e9:.1f}GB)")
        else:
            print(json.dumps(data, indent=2))
except error.HTTPError as e:
    print(f"✗ HTTP Error: {e.code} {e.reason}")
    print("  URL: http://127.0.0.1:11434/api/tags")
    sys.exit(1)
except error.URLError as e:
    print(f"✗ Connection Error: {e.reason}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

