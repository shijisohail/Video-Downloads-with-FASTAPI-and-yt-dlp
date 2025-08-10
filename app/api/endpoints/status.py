"""
Status-related API endpoints.
"""

import logging
from fastapi import APIRouter, HTTPException

from app.models.download import DownloadStatus
from app.core.storage import download_storage

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/status/{task_id}", response_model=DownloadStatus)
async def get_download_status(task_id: str):
    """Get download status for a specific task."""
    status_data = download_storage.get_status(task_id)
    
    if not status_data:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        # Clean up the status data to match the DownloadStatus model
        valid_fields = {
            "task_id", "status", "message", "download_type", "quality",
            "download_url", "filename", "total_files", "completed_files",
            "title", "url", "duration", "format", "thumbnail", "expires_at", "created_at"
        }

        # Filter status_data to only include valid fields
        filtered_data = {k: v for k, v in status_data.items() if k in valid_fields}

        # Convert duration to integer if it exists and is a float
        if 'duration' in filtered_data and filtered_data['duration'] is not None:
            try:
                filtered_data['duration'] = int(filtered_data['duration'])
            except (ValueError, TypeError):
                filtered_data['duration'] = 0

        # Only include metadata fields if download is completed
        if filtered_data.get("status") not in ["completed", "cleaned_up"]:
            # Remove metadata fields for non-completed downloads
            metadata_fields = ["title", "url", "duration", "format", "thumbnail"]
            for field in metadata_fields:
                filtered_data.pop(field, None)

        return DownloadStatus(**filtered_data)

    except Exception as e:
        logger.error(f"Error creating status response for task {task_id}: {str(e)}")
        logger.error(f"Status data: {status_data}")

        # Return a safe fallback response
        fallback_response = {
            "task_id": task_id,
            "status": status_data.get("status", "unknown"),
            "message": status_data.get("message", "Status information unavailable"),
            "download_type": status_data.get("download_type", "single"),
            "quality": status_data.get("quality", "best"),
            "download_url": status_data.get("download_url"),
            "filename": status_data.get("filename"),
            "total_files": status_data.get("total_files"),
            "completed_files": status_data.get("completed_files"),
            "expires_at": status_data.get("expires_at"),
            "created_at": status_data.get("created_at")
        }

        return DownloadStatus(**fallback_response) 