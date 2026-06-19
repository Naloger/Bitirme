# ==================== Health Endpoints ====================
from fastapi import APIRouter


router = APIRouter()


# Health check
@router.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
