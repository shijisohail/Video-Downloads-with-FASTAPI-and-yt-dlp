"""
Cleanup-related API endpoints.
"""

import logging
from fastapi import APIRouter, HTTPException

from app.services.cleanup import CleanupService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/cleanup")
async def manual_cleanup():
    """Manually trigger cleanup of old files."""
    try:
        cleanup_service = CleanupService()
        await cleanup_service.cleanup_old_files()
        return {"status": "success", "message": "Cleanup completed successfully"}
    except Exception as e:
        logger.error(f"Manual cleanup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}") 