"""Start the FastAPI application using uvicorn.

Usage (from project root):
	python Scripts/start_api.py
	python Scripts/start_api.py --host 127.0.0.1 --port 8090

This script calls uvicorn to run the app exported at
`backend.api.api:app` (a small shim to `api_init`).
"""

import sys
import argparse
from pathlib import Path

# Add backend directory to Python path if running script directly
sys.path.append(str(Path(__file__).resolve().parent.parent))

from Libs.Config.config import START_API_HOST, START_API_PORT, START_API_RELOAD


def main(host: str | None = None, port: int | None = None, reload: bool | None = None) -> None:
	"""Run the uvicorn server for the FastAPI app.

	The Python process running this script should be the virtualenv interpreter
	you want to use (so uvicorn is available). Example (PowerShell):

		# activate venv
		./.venv/Scripts/Activate.ps1

		# run the starter
		python Scripts/start_api.py
	"""

	target_host = host if host is not None else START_API_HOST
	target_port = port if port is not None else START_API_PORT
	target_reload = reload if reload is not None else START_API_RELOAD

	try:
		import uvicorn
	except Exception as exc:  # pragma: no cover - runtime dependency check
		print("uvicorn is not installed in the current environment.", file=sys.stderr)
		raise

	# Use the compatibility shim module so the recommended entrypoint works
	uvicorn.run("backend.api.api_init:app", host=target_host, port=target_port, reload=target_reload)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Start FastAPI app with uvicorn")
	parser.add_argument("--host", default=START_API_HOST, help=f"Host to bind to (default: {START_API_HOST})")
	parser.add_argument("--port", type=int, default=START_API_PORT, help=f"Port to bind to (default: {START_API_PORT})")
	parser.add_argument("--no-reload", dest="reload", action="store_false", default=START_API_RELOAD, help="Disable auto-reload")
	args = parser.parse_args()

	main(host=args.host, port=args.port, reload=args.reload)
