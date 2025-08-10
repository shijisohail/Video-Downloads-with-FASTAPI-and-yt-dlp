"""
Download service for video processing.
"""

import logging
import yt_dlp
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import settings
from app.core.storage import download_storage, file_manager
from app.utils.validation import categorize_error, validate_url_platform
from app.utils.browser import detect_browsers, extract_cookies_from_browser

logger = logging.getLogger(__name__)

class DownloadService:
    """Service for handling video downloads."""
    
    def __init__(self):
        self.downloads_dir = settings.DOWNLOADS_DIR
    
    def get_timestamp_for_filename(self) -> str:
        """Generate timestamp string for filename."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    async def download_video(self, url: str, task_id: str, download_type: str, quality: str):
        """Download video in background."""
        logger.info(f"Starting download - Task ID: {task_id}, URL: {url}, Quality: {quality}, Type: {download_type}")

        try:
            # Update status to processing
            download_storage.update_status(task_id, {
                "status": "processing",
                "message": "Downloading video..."
            })

            # Determine format based on quality
            if quality == "best":
                format_string = "best[ext=mp4]/best"
            else:
                height = quality.replace("p", "")
                format_string = f"best[ext=mp4][height<={height}]/best[ext=mp4]/mp4[height<={height}]/mp4/best[height<={height}]/best"

            # Configure yt-dlp options
            timestamp = self.get_timestamp_for_filename()
            filename_template = f"{task_id}_{timestamp}_%(title)s.%(ext)s"

            # Detect platform and find appropriate cookie file
            platform_info = validate_url_platform(url)
            platform = platform_info.get("platform", "unknown")

            # Configure yt-dlp options
            ydl_opts = self._configure_ydl_options(
                filename_template, format_string, platform
            )

            # Download the content
            info = await self._perform_download(url, ydl_opts, download_type)

            # Find the downloaded file
            downloaded_files = list(self.downloads_dir.glob(f"{task_id}_{timestamp}_*"))
            if not downloaded_files:
                raise Exception("Downloaded file not found")

            # Update status for each file
            for downloaded_file in downloaded_files:
                await self._update_download_status(task_id, info, downloaded_file)

        except Exception as e:
            error_response = categorize_error(str(e))
            download_storage.update_status(task_id, {
                "status": "failed",
                "message": error_response["user_message"],
                "error_category": error_response["category"],
                "suggestion": error_response["suggestion"],
            })
            logger.error(f"Task {task_id}: Download failed with error: {str(e)}")

    def _configure_ydl_options(self, filename_template: str, format_string: str, platform: str) -> dict:
        """Configure yt-dlp options."""
        ydl_opts = {
            "outtmpl": str(self.downloads_dir / filename_template),
            "format": format_string,
            "merge_output_format": "mp4",
            "writeinfojson": False,
            "writesubtitles": False,
            "writeautomaticsub": False,
            "ignoreerrors": False,
            "quiet": True,
            "no_warnings": True,
            "extractflat": False,
            "writethumbnail": True,
            "prefer_ffmpeg": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "http_chunk_size": settings.CHUNK_SIZE,
            "retries": settings.MAX_RETRIES,
            "fragment_retries": settings.MAX_RETRIES,
            "retry_sleep_functions": {"http": lambda n: min(3 ** n, 60)},
            "geo_bypass": True,
            "geo_bypass_country": "US",
            "age_limit": 21,
            "http_headers": self._get_http_headers(platform),
            "socket_timeout": settings.SOCKET_TIMEOUT,
            "nocheckcertificate": True,
            "extractor_retries": 5,
            "skip_unavailable_fragments": True,
            "prefer_insecure": False,
            "call_home": False,
            "continue_dl": True,
            "nopart": False,
            "youtube_include_dash_manifest": True if platform == "youtube" else False,
            "default_search": "auto",
        }

        # Add cookies if available
        cookie_file = self._get_cookie_file(platform)
        if cookie_file:
            ydl_opts["cookiefile"] = str(cookie_file)

        return ydl_opts

    def _get_http_headers(self, platform: str) -> dict:
        """Get platform-specific HTTP headers."""
        base_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "sec-ch-ua": '"Chromium";v="120", "Google Chrome";v="120", "Not:A-Brand";v="8"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

        if platform == "instagram":
            base_headers.update({
                "X-Instagram-AJAX": "1",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": "missing",
                "Referer": "https://www.instagram.com/",
                "Origin": "https://www.instagram.com",
            })
        elif platform == "facebook":
            base_headers.update({
                "Referer": "https://www.facebook.com/",
                "Origin": "https://www.facebook.com",
                "X-Requested-With": "XMLHttpRequest",
            })
        elif platform == "tiktok":
            base_headers.update({
                "Referer": "https://www.tiktok.com/",
                "Origin": "https://www.tiktok.com",
            })

        return base_headers

    def _get_cookie_file(self, platform: str) -> Path:
        """Get cookie file for platform."""
        cookie_files = {
            "youtube": ["youtube.com_cookies.txt", "youtube_cookies.txt"],
            "instagram": ["instagram.com_cookies.txt", "instagram_cookies.txt"],
            "tiktok": ["tiktok.com_cookies.txt", "tiktok_cookies.txt"],
            "twitter": ["twitter.com_cookies.txt", "x.com_cookies.txt", "twitter_cookies.txt"],
            "facebook": ["facebook.com_cookies.txt", "facebook_cookies.txt"],
            "vimeo": ["vimeo.com_cookies.txt", "vimeo_cookies.txt"],
        }

        if platform in cookie_files:
            for cookie_filename in cookie_files[platform]:
                cookie_path = settings.COOKIE_DIR / cookie_filename
                if cookie_path.exists() and cookie_path.stat().st_size > 100:
                    return cookie_path

        return None

    async def _perform_download(self, url: str, ydl_opts: dict, download_type: str):
        """Perform the actual download."""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if download_type == "single":
                info = ydl.extract_info(url, download=True)
            else:
                info = ydl.extract_info(url, download=True)

        return info

    async def _update_download_status(self, task_id: str, info: dict, downloaded_file: Path):
        """Update download status with file information."""
        filename = downloaded_file.name
        video_title = info.get("title", "Unknown Video")
        video_duration = info.get("duration", 0)
        video_url = info.get("url") or info.get("webpage_url")
        video_format = info.get("ext", "mp4")
        video_thumbnail = info.get("thumbnail")
        uploader = info.get("uploader", "Unknown")

        # Calculate expiration time (5 hours from now)
        expiration_time = datetime.now() + timedelta(hours=5)
        creation_time = datetime.now()

        # Update status to completed with video info
        download_storage.update_status(task_id, {
            "status": "completed",
            "message": f"Video downloaded successfully: {video_title}",
            "download_url": f"/api/v1/download/{task_id}",
            "filename": filename,
            "title": video_title,
            "url": video_url,
            "duration": video_duration,
            "format": video_format,
            "thumbnail": video_thumbnail,
            "expires_at": expiration_time.isoformat(),
            "created_at": creation_time.isoformat(),
        }) 