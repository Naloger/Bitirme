import sys
from pathlib import Path

# Add services directory to Python path if running script directly
sys.path.append(str(Path(__file__).resolve().parent.parent))

import uvicorn

if __name__ == "__main__":
    # Start Uvicorn programmatically
    uvicorn.run(
        # Format: "filename:app_variable_name"
        app="api.api_services_main_server:app",
        host="127.0.0.1",
        port=8100,
        reload=True,      # Auto-restarts the server when you change code
        workers=1,        # Number of worker processes
        log_level="info"  # Logging depth (debug, info, warning, error)
    )