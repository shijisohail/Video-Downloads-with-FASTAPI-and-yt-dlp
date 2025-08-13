"""
Cookie management endpoints for securely uploading cookie files to the server.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.core.config import settings
from app.services.download import DownloadService

logger = logging.getLogger(__name__)
router = APIRouter()

SUPPORTED_PLATFORMS = {"youtube", "instagram", "tiktok", "twitter", "facebook", "vimeo"}


def _cookies_dir() -> Path:
    d = settings.COOKIE_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.post("/cookies")
async def upload_cookies(
    platform: str = Form(..., description="Platform name, e.g., youtube or instagram"),
    file: UploadFile = File(..., description="Netscape-format cookie file"),
):
    """Upload a cookie file for a specific platform and validate it.

    Saves the uploaded file to /app/cookies/{platform}.com_cookies.txt and
    validates that it appears to contain Netscape-format cookies.
    """
    platform = platform.lower().strip()
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    # Determine destination filename
    filename_map = {
        "youtube": "youtube.com_cookies.txt",
        "instagram": "instagram.com_cookies.txt",
        "tiktok": "tiktok.com_cookies.txt",
        "twitter": "twitter.com_cookies.txt",
        "facebook": "facebook.com_cookies.txt",
        "vimeo": "vimeo.com_cookies.txt",
    }
    dest = _cookies_dir() / filename_map[platform]

    # Write file to destination
    content = await file.read()
    try:
        dest.write_bytes(content)
    except Exception as e:
        logger.error(f"Failed writing cookie file {dest}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save cookie file")

    # Validate using DownloadService helper
    svc = DownloadService()
    if not svc._is_valid_cookie_file(dest):  # pylint: disable=protected-access
        # Clean up invalid file
        try:
            dest.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail="Invalid cookie file format")

    logger.info(f"Uploaded cookies for {platform}: {dest} ({len(content)} bytes)")
    return {"status": "ok", "platform": platform, "path": str(dest), "size": len(content)}

