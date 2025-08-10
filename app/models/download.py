"""
Download-related data models.
"""

from typing import Optional
from pydantic import BaseModel, HttpUrl
from enum import Enum


class DownloadType(str, Enum):
    """Download type enumeration."""
    SINGLE = "single"
    PLAYLIST = "playlist"
    ALBUM = "album"


class VideoQuality(str, Enum):
    """Video quality enumeration."""
    LOW = "360p"
    MEDIUM = "480p"
    HIGH = "720p"
    VERY_HIGH = "1080p"
    ULTRA = "1440p"
    MAX = "best"


class VideoDownloadRequest(BaseModel):
    """Request model for video download."""
    url: HttpUrl
    download_type: DownloadType = DownloadType.SINGLE
    quality: VideoQuality = VideoQuality.HIGH


class DownloadResponse(BaseModel):
    """Response model for download initiation."""
    task_id: str
    status: str
    message: str
    download_type: str
    quality: str
    download_url: Optional[str] = None
    expires_at: Optional[str] = None


class DownloadStatus(BaseModel):
    """Status model for download tracking."""
    task_id: str
    status: str
    message: str
    download_type: str
    quality: str
    download_url: Optional[str] = None
    filename: Optional[str] = None
    total_files: Optional[int] = None
    completed_files: Optional[int] = None
    title: Optional[str] = None
    url: Optional[str] = None
    duration: Optional[int] = None
    format: Optional[str] = None
    thumbnail: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: Optional[str] = None 