"""
Main FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import logging

from app.api.endpoints import download, status, health, logs, cleanup
from app.core.scheduler import scheduler
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Video Downloader API",
    version=settings.VERSION,
    description="A comprehensive video downloader API supporting multiple platforms",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Mount static files for serving downloads
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(download.router, prefix="/api/v1", tags=["download"])
app.include_router(status.router, prefix="/api/v1", tags=["status"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(logs.router, prefix="/api/v1", tags=["logs"])
app.include_router(cleanup.router, prefix="/api/v1", tags=["cleanup"])

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    try:
        # Start the scheduler
        await scheduler.start()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    try:
        await scheduler.shutdown()
        logger.info("Application shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down application: {str(e)}")

@app.get("/")
async def root():
    """API root endpoint with information."""
    return {
        "message": "Video Downloader API",
        "version": settings.VERSION,
        "features": [
            "Timestamped downloads",
            "Automatic cleanup after 5 hours",
            "Enhanced error handling",
            "Multiple platform support"
        ],
        "endpoints": {
            "POST /api/v1/download": "Initiate video download",
            "GET /api/v1/status/{task_id}": "Check download status",
            "GET /api/v1/download/{task_id}": "Download completed video",
            "GET /api/v1/cleanup": "Manually trigger cleanup",
            "GET /api/v1/health": "Health check",
            "GET /api/v1/logs": "View logs",
        },
    } 