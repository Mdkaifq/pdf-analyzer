from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/status", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint to verify API is running
    """
    return {
        "status": "healthy",
        "message": "AI-Powered Document Intelligence API is running",
        "version": "1.0.0"
    }


@router.get("/ready", response_model=Dict[str, Any])
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check to verify all dependencies are available
    """
    # In a real implementation, this would check database connections,
    # external service availability, etc.
    return {
        "status": "ready",
        "checks": {
            "database": "connected",
            "llm_service": "available",
            "storage": "available"
        }
    }