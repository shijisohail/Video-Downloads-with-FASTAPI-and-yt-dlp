"""
Download service for video processing with enhanced platform support.
Implements yt-dlp best practices for Instagram, Facebook, YouTube, and TikTok.
"""

import logging
import yt_dlp
import asyncio
import os
import tempfile
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

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
        """Perform the actual download with multiple fallback strategies."""
        platform_info = validate_url_platform(url)
        platform = platform_info.get("platform", "unknown")
        
        strategies = self._get_extraction_strategies(platform, url)
        
        last_error = None
        for strategy_name, strategy_opts in strategies:
            try:
                logger.info(f"Trying extraction strategy: {strategy_name}")
                
                # Merge strategy-specific options with base options
                final_opts = {**ydl_opts, **strategy_opts}
                
                with yt_dlp.YoutubeDL(final_opts) as ydl:
                    if download_type == "single":
                        info = ydl.extract_info(url, download=True)
                    else:
                        info = ydl.extract_info(url, download=True)
                        
                logger.info(f"Successfully extracted with strategy: {strategy_name}")
                return info
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Strategy {strategy_name} failed: {last_error}")
                continue
        
        # If all strategies failed
        logger.error(f"All extraction strategies failed. Last error: {last_error}")
        raise Exception(f"Unable to download video: {last_error}")
    
    def _get_extraction_strategies(self, platform: str, url: str) -> List[tuple]:
        """Get extraction strategies based on latest yt-dlp best practices for 2024."""
        strategies = []
        
        if platform == "instagram":
            strategies.extend([
                ("instagram_mobile", self._get_instagram_mobile_options()),
                ("instagram_web", self._get_instagram_web_options()),
                ("browser_cookies", self._get_browser_cookie_options(platform)),
                ("generic_fallback", self._get_generic_options()),
            ])
        elif platform == "facebook":
            strategies.extend([
                ("facebook_web", self._get_facebook_web_options()),
                ("facebook_mobile", self._get_facebook_mobile_options()),
                ("browser_cookies", self._get_browser_cookie_options(platform)),
                ("generic_fallback", self._get_generic_options()),
            ])
        elif platform == "tiktok":
            strategies.extend([
                ("tiktok_web", self._get_tiktok_web_options()),
                ("tiktok_mobile", self._get_tiktok_mobile_options()),
                ("tiktok_api", self._get_tiktok_api_options()),
                ("generic_fallback", self._get_generic_options()),
            ])
        elif platform == "youtube":
            strategies.extend([
                ("youtube_android", self._get_youtube_android_options()),
                ("youtube_web", self._get_youtube_web_options()),
                ("youtube_ios", self._get_youtube_ios_options()),
            ])
        else:
            strategies.extend([
                ("default", {}),
                ("generic_fallback", self._get_generic_options()),
            ])
        
        return strategies
    
    def _get_instagram_full_options(self) -> dict:
        """Full Instagram extraction options."""
        return {
            "extractor_args": {
                "instagram": {
                    "api_version": "v17.0",
                    "include_stories": True,
                    "include_reels": True,
                }
            },
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6.1 Mobile/15E148 Safari/604.1",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
            },
        }
    
    def _get_instagram_optimized_options(self) -> dict:
        """Instagram-optimized extraction options."""
        return {
            "user_agent": "Instagram 276.0.0.27.98 Android (33/13; 420dpi; 1080x2280; Xiaomi; M2102J20SG; lisa; qcom; en_US; 458229237)",
            "http_headers": {
                "X-Instagram-AJAX": "1007616994",
                "X-IG-App-ID": "936619743392459",
                "X-ASBD-ID": "129477",
                "X-IG-WWW-Claim": "0",
                "Origin": "https://www.instagram.com",
                "Referer": "https://www.instagram.com/",
            },
            "sleep_interval_requests": 1,
            "sleep_interval_subtitles": 1,
        }
    
    def _get_facebook_full_options(self) -> dict:
        """Full Facebook extraction options."""
        return {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "cross-site",
            },
        }
    
    def _get_facebook_optimized_options(self) -> dict:
        """Facebook-optimized extraction options."""
        return {
            "user_agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
            "extractor_args": {
                "facebook": {
                    "api_version": "v18.0",
                }
            },
            "sleep_interval_requests": 2,
        }
    
    def _get_tiktok_full_options(self) -> dict:
        """Full TikTok extraction options."""
        return {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-CH-UA": '"Chromium";v="120", "Not:A-Brand";v="8", "Google Chrome";v="120"',
                "Sec-CH-UA-Mobile": "?0",
                "Sec-CH-UA-Platform": '"Windows"',
            },
            "extractor_args": {
                "tiktok": {
                    "api_hostname": "api16-normal-c-useast1a.tiktokv.com",
                    "use_mobile_api": True,
                }
            },
        }
    
    def _get_tiktok_optimized_options(self) -> dict:
        """TikTok-optimized extraction options."""
        return {
            "user_agent": "com.zhiliaoapp.musically/2022600040 (Linux; U; Android 7.1.2; es_ES; SM-G988N; Build/NRD90M;tt-ok/3.12.13.4-tiktok)",
            "extractor_args": {
                "tiktok": {
                    "use_mobile_api": True,
                    "api_hostname": "api22-normal-c-alisg.tiktokv.com",
                }
            },
            "http_headers": {
                "User-Agent": "com.zhiliaoapp.musically/2022600040 (Linux; U; Android 7.1.2; es_ES; SM-G988N; Build/NRD90M;tt-ok/3.12.13.4-tiktok)",
            },
            "sleep_interval_requests": 1,
        }
    
    def _get_youtube_full_options(self) -> dict:
        """Full YouTube extraction options."""
        return {
            "extractor_args": {
                "youtube": {
                    "skip": ["hls", "dash"],
                    "player_client": ["android", "web"],
                }
            },
        }
    
    def _get_youtube_optimized_options(self) -> dict:
        """YouTube-optimized extraction options."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android"],
                    "skip": ["dash"],
                }
            },
            "user_agent": "com.google.android.youtube/17.36.4 (Linux; U; Android 12) gzip",
        }
    
    def _get_simple_options(self) -> dict:
        """Simple extraction options."""
        return {
            "extractor_retries": 3,
            "fragment_retries": 3,
            "retries": 3,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
    
    def _get_browser_cookie_options(self, platform: str) -> dict:
        """Browser cookie extraction options."""
        available_browsers = detect_browsers()
        
        if not available_browsers:
            return {}
        
        # Try to get cookies from the first available browser
        try:
            browser_name = available_browsers[0]  # Use first available browser
            return {
                "cookiesfrombrowser": (browser_name, None, None, None),
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
        except Exception as e:
            logger.warning(f"Failed to setup browser cookie extraction: {e}")
            return {}
    
    # Modern 2024 extraction methods based on latest yt-dlp documentation
    
    def _get_instagram_mobile_options(self) -> dict:
        """Instagram mobile app extraction options (2024)."""
        return {
            "user_agent": "Instagram 302.0.0.23.114 Android (28/9; 480dpi; 1080x2280; samsung; SM-G973F; beyond1; exynos9820; en_US; 483971587)",
            "extractor_args": {
                "instagram": {
                    "comment_count": 0,
                }
            },
            "http_headers": {
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "en-US",
                "X-IG-App-ID": "936619743392459",
                "X-IG-WWW-Claim": "0",
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": "Instagram 302.0.0.23.114 Android (28/9; 480dpi; 1080x2280; samsung; SM-G973F; beyond1; exynos9820; en_US; 483971587)"
            },
            "sleep_interval": 1,
        }
    
    def _get_instagram_web_options(self) -> dict:
        """Instagram web extraction options (2024)."""
        return {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "max-age=0",
                "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            },
        }
    
    def _get_facebook_web_options(self) -> dict:
        """Facebook web extraction options (2024)."""
        return {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "max-age=0",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            },
        }
    
    def _get_facebook_mobile_options(self) -> dict:
        """Facebook mobile extraction options (2024)."""
        return {
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        }
    
    def _get_tiktok_web_options(self) -> dict:
        """TikTok web extraction options (2024)."""
        return {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "max-age=0",
                "Referer": "https://www.tiktok.com/",
                "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            },
        }
    
    def _get_tiktok_mobile_options(self) -> dict:
        """TikTok mobile extraction options (2024)."""
        return {
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        }
    
    def _get_tiktok_api_options(self) -> dict:
        """TikTok API extraction options (2024)."""
        return {
            "extractor_args": {
                "tiktok": {
                    "api_hostname": "api-h2.tiktokv.com",
                    "app_name": "trill",
                    "app_version": "34.1.2",
                    "manifest_app_version": "2023405020",
                    "aid": "1988",
                    "channel": "googleplay",
                    "device_platform": "android",
                    "device_type": "Redmi%20Note%208",
                    "os_version": "10"
                }
            },
            "user_agent": "com.zhiliaoapp.musically/2023405020 (Linux; U; Android 10; en_US; Redmi Note 8; Build/QKQ1.200114.002; Cronet/TTNetVersion:b4d74d15 2020-04-23 QuicVersion:0144d358 2020-03-24)"
        }
    
    def _get_youtube_android_options(self) -> dict:
        """YouTube Android client extraction options (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
        }
    
    def _get_youtube_web_options(self) -> dict:
        """YouTube web client extraction options (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["web"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        }
    
    def _get_youtube_ios_options(self) -> dict:
        """YouTube iOS client extraction options (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["ios"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "com.google.ios.youtube/19.09.3 (iPhone14,3; U; CPU iOS 15_6 like Mac OS X)",
        }
    
    def _get_generic_options(self) -> dict:
        """Generic extraction options as last resort."""
        return {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "extractor_retries": 2,
            "retries": 3,
            "fragment_retries": 3,
            "http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
        }

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
