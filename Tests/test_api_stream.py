import json

import httpx


def test_my_api_stream():
    url = "http://127.0.0.1:8100/api/v1/agent/salience/stream"
    payload = {
        "user_input": "Execute a simple loop cycle on the value 'Hello World'"
    }

    with httpx.Client(timeout=None) as client:
        with client.stream("POST", url, json=payload) as response:
            for line in response.iter_lines():
                if not line:
                    continue

                # Check if it's the plain text [Start] token instead of JSON
                if line.startswith("[Start]"):
                    print(f"System Message: {line}")
                    print("-" * 40)
                    continue

                try:
                    # Safely parse the valid JSON lines
                    chunk_data = json.loads(line)
                    print(json.dumps(chunk_data, indent=2))
                    print("-" * 40)
                except json.JSONDecodeError:
                    # Catch-all for any other unformatted logging strings
                    print(f"Raw String Frame: {line}")
