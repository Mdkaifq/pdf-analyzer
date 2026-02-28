from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio

from .routers import health_router, document_router
from .core.config import settings
from .utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown events
    """
    logger.info("Starting AI-Powered Document Intelligence API...")
    
    # Startup logic here
    logger.info("API started successfully")
    
    yield
    
    # Shutdown logic here
    logger.info("Shutting down AI-Powered Document Intelligence API...")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan
)

# Include routers
app.include_router(health_router)
app.include_router(document_router)


@app.get("/")
async def root():
    """
    Root endpoint providing API information
    """
    return {
        "message": "AI-Powered Document Intelligence API",
        "version": settings.api_version,
        "endpoints": {
            "health": "/health/status",
            "upload": "/api/v1/documents/upload",
            "process": "/api/v1/documents/process-sync"
        }
    }


# Additional middleware and configurations can be added here
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )