"""
Health check API endpoints.
"""

import logging
from fastapi import APIRouter

from app.core.config import settings
from app.core.storage import file_manager
from app.core.scheduler import scheduler

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if scheduler is running
        scheduler_status = "running" if scheduler.scheduler.running else "stopped"

        # Check downloads directory
        downloads_accessible = settings.DOWNLOADS_DIR.exists() and settings.DOWNLOADS_DIR.is_dir()

        # Count current files
        current_files = len(file_manager.list_downloads()) if downloads_accessible else 0

        return {
            "status": "healthy",
            "scheduler_status": scheduler_status,
            "downloads_directory_accessible": downloads_accessible,
            "current_files_count": current_files,
            "cleanup_enabled": True,
            "version": settings.VERSION
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        } 