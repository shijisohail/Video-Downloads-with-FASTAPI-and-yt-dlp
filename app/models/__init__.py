"""
Data models for the Video Downloader API.
"""

from .download import (
    VideoDownloadRequest,
    DownloadResponse,
    DownloadStatus,
    DownloadType,
    VideoQuality
)

__all__ = [
    "VideoDownloadRequest",
    "DownloadResponse", 
    "DownloadStatus",
    "DownloadType",
    "VideoQuality"
] 