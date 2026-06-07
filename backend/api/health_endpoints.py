# ==================== Health Endpoints ====================
from backend.api.api_init import app


# Health check
@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
