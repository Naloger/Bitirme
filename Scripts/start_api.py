"""Start the FastAPI application using uvicorn.

Usage (from project root):
	python Scripts/start_api.py
	python Scripts/start_api.py --host 127.0.0.1 --port 8090

This script calls uvicorn to run the app exported at
`backend.api.api:app` (a small shim to `api_init`).
"""

from __future__ import annotations

import argparse
import sys


def main(host: str = "127.0.0.1", port: int = 8090, reload: bool = True) -> None:
	"""Run the uvicorn server for the FastAPI app.

	The Python process running this script should be the virtualenv interpreter
	you want to use (so uvicorn is available). Example (PowerShell):

		# activate venv
		./.venv/Scripts/Activate.ps1

		# run the starter
		python Scripts/start_api.py
	"""

	try:
		import uvicorn
	except Exception as exc:  # pragma: no cover - runtime dependency check
		print("uvicorn is not installed in the current environment.", file=sys.stderr)
		raise

	# Use the compatibility shim module so the recommended entrypoint works
	uvicorn.run("backend.api.api_init:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Start FastAPI app with uvicorn")
	parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
	parser.add_argument("--port", type=int, default=8090, help="Port to bind to")
	parser.add_argument("--no-reload", dest="reload", action="store_false", help="Disable auto-reload")
	args = parser.parse_args()

	main(host=args.host, port=args.port, reload=args.reload)
