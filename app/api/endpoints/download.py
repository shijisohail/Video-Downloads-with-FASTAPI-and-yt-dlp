"""
Download-related API endpoints.
"""

import uuid
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.models.download import VideoDownloadRequest, DownloadResponse, DownloadStatus
from app.services.download import DownloadService
from app.utils.validation import is_valid_url, validate_url_platform
from app.core.storage import download_storage, file_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/download", response_model=DownloadResponse)
async def initiate_download(
    request: VideoDownloadRequest, 
    background_tasks: BackgroundTasks
):
    """Initiate video download from provided URL."""
    # Verify URL validity
    if not is_valid_url(str(request.url)):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL format. Please check the URL and try again.",
        )

    # Verify platform support
    platform_check = validate_url_platform(str(request.url))
    if not platform_check["supported"]:
        raise HTTPException(status_code=400, detail=platform_check["message"])

    # Generate unique task ID
    task_id = str(uuid.uuid4())

    # Calculate expiration time (5 hours from now)
    expiration_time = datetime.now() + timedelta(hours=5)
    creation_time = datetime.now()

    # Initialize download status
    status_data = {
        "task_id": task_id,
        "status": "initiated",
        "message": f"{request.download_type.title()} download initiated ({request.quality}) for: {str(request.url)}",
        "download_type": request.download_type.value,
        "quality": request.quality.value,
        "download_url": None,
        "filename": None,
        "total_files": None,
        "completed_files": None,
        "expires_at": expiration_time.isoformat(),
        "created_at": creation_time.isoformat(),
    }
    
    download_storage.set_status(task_id, status_data)

    # Start background download task
    try:
        download_service = DownloadService()
        background_tasks.add_task(
            download_service.download_video,
            str(request.url),
            task_id,
            request.download_type.value,
            request.quality.value,
        )
    except Exception as e:
        logger.error(f"Failed to initiate download for task {task_id}: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to initiate download")

    return DownloadResponse(
        task_id=task_id,
        status="initiated",
        message=f"{request.download_type.title()} download initiated ({request.quality}) for: {str(request.url)}",
        download_type=request.download_type.value,
        quality=request.quality.value,
        expires_at=expiration_time.isoformat(),
    )

@router.get("/download/{task_id}")
async def download_file(task_id: str):
    """Download the completed video file."""
    status_data = download_storage.get_status(task_id)
    
    if not status_data:
        raise HTTPException(status_code=404, detail="Task not found")

    if status_data["status"] == "cleaned_up":
        raise HTTPException(
            status_code=410,
            detail="File has been automatically deleted after 5 hours expiration period"
        )

    if status_data["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Download not completed. Status: {status_data['status']}",
        )

    filename = status_data.get("filename")
    if not filename or not file_manager.file_exists(filename):
        # File may have been cleaned up
        download_storage.update_status(task_id, {
            "status": "cleaned_up",
            "message": "File automatically deleted after expiration",
            "download_url": None
        })
        raise HTTPException(status_code=410, detail="Downloaded file no longer available (expired)")

    file_path = file_manager.get_download_path(filename)
    return FileResponse(
        path=str(file_path), 
        filename=filename, 
        media_type="application/octet-stream"
    ) 