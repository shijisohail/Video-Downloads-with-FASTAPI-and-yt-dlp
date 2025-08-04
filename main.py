import uuid
from pathlib import Path
from typing import Optional
import yt_dlp
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from enum import Enum
import re
import logging
import os
from datetime import datetime
import traceback
import sys
import tempfile
import subprocess
import shutil
import requests
import json
import urllib.parse
import asyncio
import aiohttp
import time

VERSION = "2.0.0"

# Setup logging configuration with absolute paths
# Get the directory where main.py is located
SCRIPT_DIR = Path(__file__).parent.absolute()
LOGS_DIR = SCRIPT_DIR / "logs"

# Create logs directory with error handling
try:
    LOGS_DIR.mkdir(exist_ok=True)
    print(f"✅ Logs directory created/exists at: {LOGS_DIR}")
except Exception as e:
    print(f"❌ Failed to create logs directory: {e}")
    print(f"📁 Attempted path: {LOGS_DIR}")
    # Fallback to current directory if script directory fails
    LOGS_DIR = Path("logs")
    try:
        LOGS_DIR.mkdir(exist_ok=True)
        print(f"✅ Fallback logs directory created at: {LOGS_DIR.absolute()}")
    except Exception as e2:
        print(f"❌ Fallback also failed: {e2}")
        # Use temp directory as last resort
        import tempfile
        LOGS_DIR = Path(tempfile.gettempdir()) / "video_downloader_logs"
        LOGS_DIR.mkdir(exist_ok=True)
        print(f"⚠️ Using temp directory for logs: {LOGS_DIR}")

# Configure logging
log_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)

# File handler for all logs
file_handler = logging.FileHandler(LOGS_DIR / 'video_downloader.log')
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)

# File handler for errors only
error_handler = logging.FileHandler(LOGS_DIR / 'errors.log')
error_handler.setFormatter(log_formatter)
error_handler.setLevel(logging.ERROR)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# Setup logger
logger = logging.getLogger("video_downloader_api")
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(error_handler)
logger.addHandler(console_handler)

# Prevent duplicate logs
logger.propagate = False

# Log startup
logger.info(f"=== Video Downloader API v{VERSION} Starting ===")
logger.info(f"Logs directory: {LOGS_DIR.absolute()}")
logger.info(f"Downloads directory: {Path('downloads').absolute()}")

app = FastAPI(title="Video Downloader API", version=f"{VERSION}")

# Mount static files for serving downloads
app.mount("/static", StaticFiles(directory="static"), name="static")

# Directory to store downloaded videos with absolute path
DOWNLOADS_DIR = SCRIPT_DIR / "downloads"
try:
    DOWNLOADS_DIR.mkdir(exist_ok=True)
    print(f"✅ Downloads directory created/exists at: {DOWNLOADS_DIR}")
except Exception as e:
    print(f"❌ Failed to create downloads directory: {e}")
    print(f"📁 Attempted path: {DOWNLOADS_DIR}")
    # Fallback to current directory
    DOWNLOADS_DIR = Path("downloads")
    try:
        DOWNLOADS_DIR.mkdir(exist_ok=True)
        print(f"✅ Fallback downloads directory created at: {DOWNLOADS_DIR.absolute()}")
    except Exception as e2:
        print(f"❌ Downloads directory fallback failed: {e2}")
        # Use temp directory as last resort
        import tempfile
        DOWNLOADS_DIR = Path(tempfile.gettempdir()) / "video_downloader_downloads"
        DOWNLOADS_DIR.mkdir(exist_ok=True)
        print(f"⚠️ Using temp directory for downloads: {DOWNLOADS_DIR}")

# In-memory storage for download status (in production, use a database)
download_status = {}


# Error handling functions
def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+"  # domain
        r"(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # host
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return bool(url_pattern.match(url))


def categorize_error(error_message: str) -> dict:
    """Categorize error messages for better user feedback"""
    error_lower = error_message.lower()

    if "private" in error_lower or "unavailable" in error_lower:
        return {
            "category": "PRIVATE_VIDEO",
            "user_message": "This video is private or unavailable. Please check if the video is publicly accessible.",
            "suggestion": "Try a different video URL or contact the video owner.",
        }

    elif "geo" in error_lower or "region" in error_lower or "country" in error_lower:
        return {
            "category": "GEO_RESTRICTED",
            "user_message": "This video is not available in your region due to geographical restrictions.",
            "suggestion": "This content may be restricted in your location.",
        }

    elif "age" in error_lower or "restricted" in error_lower:
        return {
            "category": "AGE_RESTRICTED",
            "user_message": "This video is age-restricted and cannot be downloaded.",
            "suggestion": "Age-restricted content requires special authentication.",
        }

    elif "copyright" in error_lower or "dmca" in error_lower:
        return {
            "category": "COPYRIGHT",
            "user_message": "This video is protected by copyright and cannot be downloaded.",
            "suggestion": "Please respect copyright restrictions.",
        }

    elif "format" in error_lower or "no video" in error_lower:
        return {
            "category": "FORMAT_ERROR",
            "user_message": "No suitable video format found for download.",
            "suggestion": "Try selecting a different quality or check if the video supports downloads.",
        }

    elif (
        "network" in error_lower
        or "timeout" in error_lower
        or "connection" in error_lower
    ):
        return {
            "category": "NETWORK_ERROR",
            "user_message": "Network error occurred while downloading the video.",
            "suggestion": "Please check your internet connection and try again.",
        }

    elif "not found" in error_lower or "404" in error_lower:
        return {
            "category": "VIDEO_NOT_FOUND",
            "user_message": "Video not found. The URL may be incorrect or the video may have been deleted.",
            "suggestion": "Please verify the URL and try again.",
        }

    elif "live" in error_lower or "stream" in error_lower:
        return {
            "category": "LIVE_STREAM",
            "user_message": "Live streams cannot be downloaded while they are active.",
            "suggestion": "Wait for the stream to end or try downloading a recorded version.",
        }

    elif "login" in error_lower or "authentication" in error_lower:
        return {
            "category": "AUTH_REQUIRED",
            "user_message": "This video requires authentication to access.",
            "suggestion": "This content may require login credentials.",
        }

    else:
        return {
            "category": "GENERAL_ERROR",
            "user_message": "An error occurred while processing your request.",
            "suggestion": "Please try again later or contact support if the issue persists.",
        }


def validate_url_platform(url: str) -> dict:
    """Validate if the URL is from a supported platform"""
    supported_patterns = {
        "youtube": [r"youtube\.com", r"youtu\.be"],
        "tiktok": [r"tiktok\.com"],
        "instagram": [r"instagram\.com"],
        "twitter": [r"twitter\.com", r"x\.com"],
        "facebook": [r"facebook\.com", r"fb\.watch"],
        "vimeo": [r"vimeo\.com"],
        "dailymotion": [r"dailymotion\.com"],
        "twitch": [r"twitch\.tv"],
    }

    for platform, patterns in supported_patterns.items():
        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return {"supported": True, "platform": platform}

    return {
        "supported": False,
        "platform": "unknown",
        "message": "URL may not be from a supported platform. Supported platforms include YouTube, TikTok, Instagram, Twitter, Facebook, Vimeo, and more.",
    }


class DownloadType(str, Enum):
    SINGLE = "single"
    PLAYLIST = "playlist"
    ALBUM = "album"


class VideoQuality(str, Enum):
    LOW = "360p"  # 360p
    MEDIUM = "480p"  # 480p
    HIGH = "720p"  # 720p (default)
    VERY_HIGH = "1080p"  # 1080p
    ULTRA = "1440p"  # 1440p
    MAX = "best"  # Best available


class VideoDownloadRequest(BaseModel):
    url: HttpUrl
    download_type: DownloadType = DownloadType.SINGLE
    quality: VideoQuality = VideoQuality.HIGH


class DownloadResponse(BaseModel):
    task_id: str
    status: str
    message: str
    download_type: str
    quality: str
    download_url: Optional[str] = None


class DownloadStatus(BaseModel):
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


def detect_browsers():
    """Detect available browsers for cookie extraction"""
    browsers = []
    
    # Common browser paths and names (prioritize Chrome for better social media support)
    browser_configs = {
        "chrome": ["google-chrome", "chrome", "chromium", "google-chrome-stable"],
        "firefox": ["firefox", "firefox-esr"],
        "edge": ["microsoft-edge", "msedge"],
        "safari": ["safari"],
        "opera": ["opera"],
    }
    
    for browser_name, commands in browser_configs.items():
        for cmd in commands:
            if shutil.which(cmd):
                browsers.append(browser_name)
                logger.debug(f"Detected browser: {browser_name} (command: {cmd})")
                break
    
    logger.info(f"Available browsers for cookie extraction: {browsers}")
    return browsers


def create_social_media_headers(platform: str) -> dict:
    """Create platform-specific headers for social media platforms"""
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


def extract_cookies_from_browser(platform: str, browsers: list) -> Optional[str]:
    """Extract cookies from browser and save to temporary file"""
    if not browsers:
        return None
    
    # Try each available browser
    for browser in browsers:
        try:
            logger.info(f"Attempting to extract {platform} cookies from {browser}")
            
            # Create temporary cookie file
            temp_cookie_file = tempfile.NamedTemporaryFile(
                mode='w', suffix=f'_{platform}_cookies.txt', delete=False
            )
            temp_cookie_file.close()
            
            # Configure yt-dlp to extract cookies
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "cookiesfrombrowser": (browser, None, None, None),
                "cookiefile": temp_cookie_file.name,
                "writecookiefile": True,
                "extract_flat": True,
                "simulate": True,  # Don't actually download
            }
            
            # Use a simple URL to test cookie extraction
            test_urls = {
                "youtube": "https://www.youtube.com",
                "instagram": "https://www.instagram.com",
                "tiktok": "https://www.tiktok.com",
                "twitter": "https://twitter.com",
                "facebook": "https://www.facebook.com",
                "vimeo": "https://vimeo.com",
            }
            
            test_url = test_urls.get(platform, "https://www.youtube.com")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    # This will extract cookies and save them
                    ydl.extract_info(test_url, download=False)
                    
                    # Check if cookie file was created and has content
                    if os.path.exists(temp_cookie_file.name) and os.path.getsize(temp_cookie_file.name) > 0:
                        logger.info(f"Successfully extracted {platform} cookies from {browser}")
                        return temp_cookie_file.name
                    else:
                        os.unlink(temp_cookie_file.name)
                        
                except Exception as e:
                    logger.debug(f"Failed to extract cookies from {browser} for {platform}: {str(e)}")
                    if os.path.exists(temp_cookie_file.name):
                        os.unlink(temp_cookie_file.name)
                    continue
                    
        except Exception as e:
            logger.debug(f"Browser {browser} cookie extraction failed: {str(e)}")
            continue
    
    logger.warning(f"Could not extract {platform} cookies from any available browser")
    return None


def get_video_info(url: str):
    """Get video information without downloading"""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 10,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", "Unknown"),
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", "Unknown"),
            }
        except Exception as e:
            raise Exception(f"Failed to get video info: {str(e)}")


async def download_video(url: str, task_id: str, download_type: str, quality: str):
    """Download video in background"""
    logger.info(f"Starting download - Task ID: {task_id}, URL: {url}, Quality: {quality}, Type: {download_type}")
    
    try:
        # Update status to processing
        download_status[task_id]["status"] = "processing"
        download_status[task_id]["message"] = "Downloading video..."
        logger.debug(f"Task {task_id}: Status updated to processing")

        # Determine format based on quality
        if quality == "best":
            format_string = "best[ext=mp4]/best"
        else:
            height = quality.replace(
                "p", ""
            )  # Remove 'p' from quality like '720p' -> '720'
            format_string = f"best[ext=mp4][height<={height}]/best[ext=mp4]/mp4[height<={height}]/mp4/best[height<={height}]/best"
        
        logger.debug(f"Task {task_id}: Format string: {format_string}")

        # Configure yt-dlp options for download
        filename_template = f"{task_id}_%(title)s.%(ext)s"
        
        # Detect platform and find appropriate cookie file
        platform_info = validate_url_platform(url)
        platform = platform_info.get("platform", "unknown")
        
        # Cookie file mapping for different platforms
        cookie_files = {
            "youtube": ["youtube.com_cookies.txt", "youtube_cookies.txt"],
            "instagram": ["instagram.com_cookies.txt", "instagram_cookies.txt"],
            "tiktok": ["tiktok.com_cookies.txt", "tiktok_cookies.txt"],
            "twitter": ["twitter.com_cookies.txt", "x.com_cookies.txt", "twitter_cookies.txt"],
            "facebook": ["facebook.com_cookies.txt", "facebook_cookies.txt"],
            "vimeo": ["vimeo.com_cookies.txt", "vimeo_cookies.txt"],
            "dailymotion": ["dailymotion.com_cookies.txt", "dailymotion_cookies.txt"],
            "twitch": ["twitch.tv_cookies.txt", "twitch_cookies.txt"],
        }
        
        # Find appropriate cookie file or extract from browser
        selected_cookie_file = None
        dynamic_cookie_file = None
        
        # First, try existing cookie files with validation
        if platform in cookie_files:
            for cookie_filename in cookie_files[platform]:
                cookie_path = SCRIPT_DIR / cookie_filename
                if cookie_path.exists() and os.path.getsize(cookie_path) > 100:
                    # Validate cookie file format
                    try:
                        with open(cookie_path, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            # Check if it's a valid Netscape cookie format or has content
                            if content and (content.startswith('# Netscape HTTP Cookie File') or '\t' in content):
                                selected_cookie_file = cookie_path
                                logger.info(f"Task {task_id}: Found valid cookies for {platform}: {cookie_filename}")
                                break
                            else:
                                logger.debug(f"Task {task_id}: Cookie file {cookie_filename} has invalid format")
                    except Exception as e:
                        logger.debug(f"Task {task_id}: Error reading cookie file {cookie_filename}: {e}")
        
        # If no platform-specific cookies found, try generic cookies file
        if not selected_cookie_file:
            generic_cookies = SCRIPT_DIR / "cookies.txt"
            if generic_cookies.exists() and os.path.getsize(generic_cookies) > 100:
                try:
                    with open(generic_cookies, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content and (content.startswith('# Netscape HTTP Cookie File') or '\t' in content):
                            selected_cookie_file = generic_cookies
                            logger.info(f"Task {task_id}: Using valid generic cookies file")
                except Exception as e:
                    logger.debug(f"Task {task_id}: Error reading generic cookie file: {e}")
        
        # If no existing cookies, try to extract from browser dynamically
        if not selected_cookie_file:
            logger.info(f"Task {task_id}: No existing cookies found, attempting dynamic extraction for {platform}")
            available_browsers = detect_browsers()
            
            if available_browsers:
                dynamic_cookie_file = extract_cookies_from_browser(platform, available_browsers)
                if dynamic_cookie_file:
                    selected_cookie_file = Path(dynamic_cookie_file)
                    logger.info(f"Task {task_id}: Successfully extracted dynamic cookies for {platform}")
                else:
                    logger.warning(f"Task {task_id}: Dynamic cookie extraction failed for {platform}")
        
        ydl_opts = {
            "outtmpl": str(DOWNLOADS_DIR / filename_template),
            "format": format_string,
            "merge_output_format": "mp4",
            "writeinfojson": False,
            "writesubtitles": False,
            "writeautomaticsub": False,
            "ignoreerrors": False,
            "quiet": True,
            "no_warnings": True,
            "extractflat": download_type != "single",  # Flat playlist/album extraction for non-single
            "writethumbnail": True,
            "prefer_ffmpeg": True,
            # Enhanced options for better compatibility and bot detection avoidance
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "http_chunk_size": 10485760,  # 10MB chunks
            "retries": 10,  # Increased retries for better reliability
            "fragment_retries": 10,
            "retry_sleep_functions": {"http": lambda n: min(3 ** n, 60)},  # Exponential backoff
            # Geo and age bypass options
            "geo_bypass": True,
            "geo_bypass_country": "US",
            "age_limit": 21,
            # Enhanced headers to avoid bot detection
            "http_headers": {
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
            },
            # Network optimizations
            "socket_timeout": 60,  # Increased timeout
            "source_address": None,
            # Additional platform-specific options
            "nocheckcertificate": True,
            # Platform-specific optimizations
            "extractor_retries": 5,
            "skip_unavailable_fragments": True,
            # Multi-server support - try multiple CDNs/servers
            "prefer_insecure": False,
            "call_home": False,
            # Enhanced error recovery
            "continue_dl": True,
            "nopart": False,
            # Platform-specific tweaks
            "youtube_include_dash_manifest": True if platform == "youtube" else False,
            # Generic extractor fallbacks
            "default_search": "auto",
        }
        
        # Add cookies if found
        if selected_cookie_file:
            ydl_opts["cookiefile"] = str(selected_cookie_file)
            logger.info(f"Task {task_id}: Using cookies file: {selected_cookie_file}")
        else:
            logger.warning(f"Task {task_id}: No cookies available for {platform}. Trying without authentication.")
            # For platforms that typically need authentication, try browser cookies as final fallback
            if platform in ["youtube", "instagram", "tiktok", "twitter", "facebook"]:
                available_browsers = detect_browsers()
                if available_browsers:
                    try:
                        # Try the first available browser
                        primary_browser = available_browsers[0]
                        ydl_opts["cookiesfrombrowser"] = (primary_browser, None, None, None)
                        logger.info(f"Task {task_id}: Attempting to use {primary_browser} browser cookies as final fallback")
                    except Exception as e:
                        logger.debug(f"Task {task_id}: Browser cookies final fallback failed: {str(e)}")
        
        logger.debug(f"Task {task_id}: yt-dlp options configured: {ydl_opts}")
        logger.info(f"Task {task_id}: Starting yt-dlp extraction for {url}")

        # Download the content with enhanced error handling and multi-server support
        download_successful = False
        last_error = None
        
        # Platform-specific extraction strategies for better reliability
        extraction_strategies = []
        
        # Strategy 1: Full extraction with all options
        extraction_strategies.append({"strategy": "full", "opts": ydl_opts.copy()})
        
        # Strategy 2: Platform-specific optimized extraction
        if platform == "instagram":
            instagram_opts = ydl_opts.copy()
            instagram_opts.update({
                "format": "best[ext=mp4]/best",
                "http_headers": {
                    **ydl_opts["http_headers"],
                    "X-Instagram-AJAX": "1",
                    "X-Requested-With": "XMLHttpRequest",
                },
                "extract_flat": False,
                "no_check_certificates": True,
            })
            extraction_strategies.append({"strategy": "instagram_optimized", "opts": instagram_opts})
            
        elif platform == "tiktok":
            tiktok_opts = ydl_opts.copy()
            tiktok_opts.update({
                "format": "best[ext=mp4]/best",
                "http_headers": {
                    **ydl_opts["http_headers"],
                    "Referer": "https://www.tiktok.com/",
                },
                "extract_flat": False,
            })
            extraction_strategies.append({"strategy": "tiktok_optimized", "opts": tiktok_opts})
            
        elif platform == "facebook":
            facebook_opts = ydl_opts.copy()
            facebook_opts.update({
                "format": "best[ext=mp4]/best",
                "http_headers": {
                    **ydl_opts["http_headers"],
                    "Referer": "https://www.facebook.com/",
                },
                "extract_flat": False,
            })
            extraction_strategies.append({"strategy": "facebook_optimized", "opts": facebook_opts})
        
        # Strategy 3: Simplified extraction for compatibility
        simplified_opts = {
            k: v for k, v in ydl_opts.items() if k in [
                "outtmpl", "format", "quiet", "no_warnings", "retries", "fragment_retries",
                "socket_timeout", "user_agent", "http_headers", "cookiefile", "cookiesfrombrowser"
            ]
        }
        extraction_strategies.append({"strategy": "simple", "opts": simplified_opts})
        
        # Strategy 4: Fallback with browser cookies only (for social media)
        if platform in ["instagram", "tiktok", "facebook", "twitter"]:
            available_browsers = detect_browsers()
            if available_browsers:
                browser_opts = {
                    "outtmpl": ydl_opts["outtmpl"],
                    "format": "best[ext=mp4]/best",
                    "quiet": True,
                    "no_warnings": True,
                    "user_agent": ydl_opts["user_agent"],
                    "socket_timeout": 45,
                    "cookiesfrombrowser": (available_browsers[0], None, None, None),
                    "http_headers": ydl_opts["http_headers"],
                }
                extraction_strategies.append({"strategy": "browser_cookies", "opts": browser_opts})
        
        # Strategy 5: Generic extractor fallback
        generic_opts = {
            "outtmpl": ydl_opts["outtmpl"],
            "format": "best[ext=mp4]/best",
            "quiet": True,
            "no_warnings": True,
            "user_agent": ydl_opts["user_agent"],
            "socket_timeout": 30,
        }
        extraction_strategies.append({"strategy": "generic", "opts": generic_opts})
        
        for strategy_info in extraction_strategies:
            strategy_name = strategy_info["strategy"]
            strategy_opts = strategy_info["opts"]
            
            logger.info(f"Task {task_id}: Trying extraction strategy: {strategy_name}")
            
            try:
                with yt_dlp.YoutubeDL(strategy_opts) as ydl:
                    if download_type == "single":
                        logger.debug(f"Task {task_id}: Extracting single video with {strategy_name} strategy")
                        info = ydl.extract_info(url, download=True)
                    else:
                        logger.debug(f"Task {task_id}: Extracting {download_type} with {strategy_name} strategy")
                        info = ydl.extract_info(url, download=True)
                        # Count total and completed files
                        total_files = sum(1 for file in (info.get("entries") or []))
                        completed_files = len(DOWNLOADS_DIR.glob(f"{task_id}_*"))
                        download_status[task_id]["total_files"] = total_files
                        download_status[task_id]["completed_files"] = completed_files
                        logger.debug(f"Task {task_id}: Playlist/Album - Total: {total_files}, Completed: {completed_files}")
                    
                    logger.info(f"Task {task_id}: yt-dlp extraction completed successfully with {strategy_name} strategy")
                    logger.debug(f"Task {task_id}: Video info - Title: {info.get('title', 'Unknown')}, Duration: {info.get('duration', 0)}s")
                    download_successful = True
                    break
                    
            except Exception as ytdl_error:
                logger.warning(f"Task {task_id}: Strategy {strategy_name} failed: {str(ytdl_error)}")
                last_error = ytdl_error
                continue
        
        if not download_successful:
            logger.error(f"Task {task_id}: All extraction strategies failed")
            logger.error(f"Task {task_id}: Final error: {str(last_error)}")
            logger.error(f"Task {task_id}: Full traceback: {traceback.format_exc()}")
            raise last_error

        # Find the downloaded file
        downloaded_files = list(DOWNLOADS_DIR.glob(f"{task_id}_*"))
        if not downloaded_files:
            raise Exception("Downloaded file not found")

        for downloaded_file in downloaded_files:
            # Update status for each file
            filename = downloaded_file.name

            # Extract video information
            video_title = info.get("title", "Unknown Video")
            video_duration = info.get("duration", 0)
            video_url = info.get("url") or info.get("webpage_url")
            video_format = info.get("ext", "mp4")
            video_thumbnail = info.get("thumbnail")
            uploader = info.get("uploader", "Unknown")

            # Update status to completed with video info
            download_status[task_id].update(
                {
                    "status": "completed",
                    "message": f"Video downloaded successfully: {video_title}",
                    "download_url": f"/download/{task_id}",
                    "filename": filename,
                    "title": video_title,
                    "url": video_url,
                    "duration": video_duration,
                    "format": video_format,
                    "thumbnail": video_thumbnail,
                }
            )

    except Exception as e:
        error_response = categorize_error(str(e))
        download_status[task_id].update(
            {
                "status": "failed",
                "message": error_response["user_message"],
                "error_category": error_response["category"],
                "suggestion": error_response["suggestion"],
            }
        )
        logger.error(f"Task {task_id}: Download failed with error: {str(e)}")
    
    finally:
        # Clean up any temporary cookie files
        if dynamic_cookie_file and os.path.exists(dynamic_cookie_file):
            try:
                os.unlink(dynamic_cookie_file)
                logger.debug(f"Task {task_id}: Cleaned up temporary cookie file: {dynamic_cookie_file}")
            except Exception as cleanup_error:
                logger.warning(f"Task {task_id}: Failed to clean up temporary cookie file: {cleanup_error}")


@app.post("/download", response_model=DownloadResponse)
async def initiate_download(
    request: VideoDownloadRequest, background_tasks: BackgroundTasks
):
    """Initiate video download from provided URL"""
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

    # Initialize download status immediately
    download_status[task_id] = {
        "task_id": task_id,
        "status": "initiated",
        "message": f"{request.download_type.title()} download initiated ({request.quality}) for: {str(request.url)}",
        "download_type": request.download_type.value,
        "quality": request.quality.value,
        "download_url": None,
        "filename": None,
        "total_files": None,
        "completed_files": None,
    }

    # Start background download task
    try:
        background_tasks.add_task(
            download_video,
            str(request.url),
            task_id,
            request.download_type.value,
            request.quality.value,
        )
    except Exception as e:
        error_response = categorize_error(str(e))
        download_status[task_id].update(
            {
                "status": "failed",
                "message": error_response["user_message"],
            }
        )
        raise HTTPException(status_code=400, detail=error_response["user_message"])

    return DownloadResponse(
        task_id=task_id,
        status="initiated",
        message=f"{request.download_type.title()} download initiated ({request.quality}) for: {str(request.url)}",
        download_type=request.download_type.value,
        quality=request.quality.value,
    )


@app.get("/status/{task_id}")
async def get_download_status(task_id: str):
    """Get download status for a specific task"""
    if task_id not in download_status:
        raise HTTPException(status_code=404, detail="Task not found")

    status_data = download_status[task_id].copy()

    # Only include metadata fields if download is completed
    if status_data.get("status") != "completed":
        # Remove metadata fields for non-completed downloads
        metadata_fields = ["title", "url", "duration", "format", "thumbnail"]
        for field in metadata_fields:
            status_data.pop(field, None)

        # Create response model excluding metadata fields
        exclude_fields = {"title", "url", "duration", "format", "thumbnail"}
        response = DownloadStatus(**status_data)
        return JSONResponse(content=response.model_dump(exclude=exclude_fields))
    else:
        # Include all fields for completed downloads
        return DownloadStatus(**status_data)


@app.get("/download/{task_id}")
async def download_file(task_id: str):
    """Download the completed video file"""
    if task_id not in download_status:
        raise HTTPException(status_code=404, detail="Task not found")

    status = download_status[task_id]

    if status["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Download not completed. Status: {status['status']}",
        )

    # Find the downloaded file
    downloaded_files = list(DOWNLOADS_DIR.glob(f"{task_id}_*"))
    if not downloaded_files:
        raise HTTPException(status_code=404, detail="Downloaded file not found")

    file_path = downloaded_files[0]
    filename = status.get("filename", file_path.name)

    return FileResponse(
        path=str(file_path), filename=filename, media_type="application/octet-stream"
    )


@app.get("/")
async def root():
    """API health check and information"""
    return {
        "message": "Video Downloader API",
        "version": f"{VERSION}",
        "endpoints": {
            "POST /download": "Initiate video download",
            "GET /status/{task_id}": "Check download status",
            "GET /download/{task_id}": "Download completed video",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/logs")
async def get_logs_info():
    """Get information about available log files"""
    try:
        log_files = []
        if LOGS_DIR.exists():
            for log_file in LOGS_DIR.glob("*.log"):
                stat = log_file.stat()
                log_files.append({
                    "filename": log_file.name,
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "url": f"/logs/{log_file.name}"
                })
        
        return {
            "logs_directory": str(LOGS_DIR),
            "available_logs": log_files,
            "total_files": len(log_files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error accessing logs: {str(e)}")


@app.get("/logs/{filename}")
async def get_log_file(filename: str, lines: int = 100):
    """Get log file contents (last N lines)"""
    try:
        log_file_path = LOGS_DIR / filename
        
        # Security check - only allow .log files
        if not filename.endswith(".log"):
            raise HTTPException(status_code=400, detail="Only .log files are allowed")
        
        if not log_file_path.exists():
            raise HTTPException(status_code=404, detail="Log file not found")
        
        # Read the last N lines
        with open(log_file_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {
            "filename": filename,
            "total_lines": len(all_lines),
            "returned_lines": len(last_lines),
            "requested_lines": lines,
            "content": ''.join(last_lines)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading log file: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8888)
