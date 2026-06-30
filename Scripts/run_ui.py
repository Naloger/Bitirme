"""Start the Frontend chat UI server.

Usage (from project root):
    python frontend/Scripts/run_ui.py
    python frontend/Scripts/run_ui.py --host 127.0.0.1 --port 8080
"""

import sys
import argparse
from pathlib import Path

# Add frontend directory to Python path if running script directly
sys.path.append(str(Path(__file__).resolve().parent.parent))

HOST = "127.0.0.1"
PORT = 8110


def main(host: str = HOST, port: int = PORT, reload: bool = True) -> None:
    try:
        import uvicorn
    except ImportError:
        print("uvicorn is not installed. Run 'uv sync' inside the frontend/ directory.", file=sys.stderr)
        raise

    uvicorn.run("frontend.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the Salience Chat UI")
    parser.add_argument("--host", default=HOST, help=f"Host to bind (default: {HOST})")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port to bind (default: {PORT})")
    parser.add_argument("--no-reload", dest="reload", action="store_false", default=True)
    args = parser.parse_args()

    main(host=args.host, port=args.port, reload=args.reload)
