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

    def _configure_ydl_options(self, filename_template: str, format_string: str, platform: str, force_no_cookies: bool = False) -> dict:
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

        # Only add cookies if not forcing no cookies and cookies are valid
        if not force_no_cookies:
            cookie_file = self._get_cookie_file(platform)
            if cookie_file:
                ydl_opts["cookiefile"] = str(cookie_file)
                logger.info(f"Using valid cookie file for {platform}: {cookie_file}")
            else:
                logger.info(f"No valid cookie file found for {platform}, proceeding without cookies")

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
        """Get cookie file for platform if valid, otherwise return None."""
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
                    # Validate cookie file format
                    if self._is_valid_cookie_file(cookie_path):
                        return cookie_path
                    else:
                        logger.warning(f"Cookie file {cookie_path} exists but has invalid format, skipping")

        return None
    
    def _is_valid_cookie_file(self, cookie_path: Path) -> bool:
        """Check if cookie file is in valid Netscape format."""
        try:
            with open(cookie_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            # Empty file is invalid
            if not content:
                return False
                
            # Check for Netscape format header or valid cookie lines
            lines = content.split('\n')
            valid_lines = 0
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                # Valid Netscape cookie format: domain\tflag\tpath\tsecure\texpires\tname\tvalue
                parts = line.split('\t')
                if len(parts) >= 7:
                    valid_lines += 1
                elif len(parts) >= 3:  # More lenient check for some cookie formats
                    valid_lines += 1
            
            return valid_lines > 0
            
        except Exception as e:
            logger.warning(f"Error validating cookie file {cookie_path}: {e}")
            return False

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
                
                # If strategy explicitly sets no_cookies or cookiefile=None, remove any cookiefile from base options
                if strategy_opts.get("no_cookies") or strategy_opts.get("cookiefile") is None:
                    final_opts.pop("cookiefile", None)
                
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
                ("instagram_anonymous", self._get_instagram_anonymous_options()),
                ("instagram_api_bypass", self._get_instagram_api_bypass_options()),
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
                # Most reliable strategies first - VR client often bypasses restrictions
                ("youtube_android_vr_no_cookies", self._get_youtube_android_vr_no_cookies_options()),
                ("youtube_android_testsuite_no_cookies", self._get_youtube_android_testsuite_no_cookies_options()),
                ("youtube_android_tv_no_cookies", self._get_youtube_no_cookies_android_tv_options()),
                ("youtube_android_music_no_cookies", self._get_youtube_android_music_no_cookies_options()),
                ("youtube_ios_music_no_cookies", self._get_youtube_ios_music_no_cookies_options()),
                ("youtube_mweb_no_cookies", self._get_youtube_mweb_no_cookies_options()),
                ("youtube_web_embedded_no_cookies", self._get_youtube_web_embedded_no_cookies_options()),
                
                # Additional VR and specialized clients
                ("youtube_android_producer", self._get_youtube_android_producer_options()),
                ("youtube_android_unplugged", self._get_youtube_android_unplugged_options()),
                
                # Fallback with potentially more permissive settings
                ("youtube_android_creator", self._get_youtube_android_creator_options()),
                ("youtube_web_creator", self._get_youtube_web_creator_options()),
                ("youtube_tvhtml5_no_cookies", self._get_youtube_tvhtml5_no_cookies_options()),
                
                # Original strategies as final fallback
                ("youtube_android_tv", self._get_youtube_android_tv_options()),
                ("youtube_android", self._get_youtube_android_options()),
                ("youtube_web", self._get_youtube_web_options()),
                ("generic_fallback", self._get_generic_options()),
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
    
    def _get_youtube_android_tv_options(self) -> dict:
        """YouTube Android TV client extraction options - often bypasses authentication (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_tv"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "com.google.android.tv.youtube/4.40.30 (Linux; U; Android 9; sm-t720; Build/PPR1.180610.011) gzip",
        }
    
    def _get_youtube_web_embedded_options(self) -> dict:
        """YouTube web embedded player options - bypasses some restrictions (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["web_embedded_player"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "http_headers": {
                "Origin": "https://www.youtube.com",
                "Referer": "https://www.youtube.com/",
            },
        }
    
    def _get_youtube_age_bypass_options(self) -> dict:
        """YouTube age verification bypass options (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_embedded"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
            "age_limit": None,  # Remove age limit restriction
            "http_headers": {
                "X-YouTube-Client-Name": "3",
                "X-YouTube-Client-Version": "17.31.35",
            },
        }
    
    def _get_youtube_unrestricted_options(self) -> dict:
        """YouTube unrestricted access options for public content (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_testsuite"],
                    "player_skip": ["configs", "js"],
                }
            },
            "user_agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
            "http_headers": {
                "X-YouTube-Client-Name": "30",
                "X-YouTube-Client-Version": "19.09.37",
            },
            "age_limit": None,
            "geo_bypass": True,
        }
    
    def _get_youtube_public_content_options(self) -> dict:
        """YouTube public content access without authentication (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["web_creator"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        }
    
    def _get_youtube_music_options(self) -> dict:
        """YouTube Music client - often has fewer restrictions (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_music"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "com.google.android.apps.youtube.music/5.26.1 (Linux; U; Android 11; en_US) gzip",
            "http_headers": {
                "X-YouTube-Client-Name": "21",
                "X-YouTube-Client-Version": "5.26.1",
            },
        }
    
    def _get_youtube_android_testsuite_options(self) -> dict:
        """YouTube Android testsuite client - bypasses many restrictions (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_testsuite"],
                    "player_skip": ["configs", "webpage"],
                }
            },
            "user_agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
            "http_headers": {
                "X-YouTube-Client-Name": "30",
                "X-YouTube-Client-Version": "19.09.37",
            },
            "format": "best[ext=mp4]/mp4/best",
        }
    
    def _get_youtube_media_connect_options(self) -> dict:
        """YouTube Media Connect client - for content creators (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["media_connect_frontend"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "http_headers": {
                "X-YouTube-Client-Name": "95",
                "X-YouTube-Client-Version": "1.0",
            },
        }
    
    def _get_youtube_no_auth_options(self) -> dict:
        """YouTube with minimal authentication requirements (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_embedded"],
                    "player_skip": ["configs", "webpage", "js"],
                }
            },
            "user_agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
            "format": "worst[ext=mp4]/worst",  # Try lower quality first
            "age_limit": None,
            "geo_bypass": True,
            "no_check_certificate": True,
            "http_headers": {
                "Accept": "*/*",
                "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
            },
        }
    
    def _get_instagram_anonymous_options(self) -> dict:
        """Instagram anonymous access options (2024)."""
        return {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            },
            "extractor_args": {
                "instagram": {
                    "api_version": "v1.0",
                    "extract_flat": False,
                }
            },
            "format": "best[ext=mp4]/mp4/best",
        }
    
    def _get_instagram_api_bypass_options(self) -> dict:
        """Instagram API bypass options for public content (2024)."""
        return {
            "user_agent": "InstagramBot/1.0 (+https://www.instagram.com/)",
            "http_headers": {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "X-Requested-With": "XMLHttpRequest",
                "X-IG-App-ID": "936619743392459",
                "X-Instagram-AJAX": "1",
                "X-CSRFToken": "missing",
                "X-IG-WWW-Claim": "0",
                "DNT": "1",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            },
            "extractor_args": {
                "instagram": {
                    "api_version": "v17.0",
                    "use_public_endpoint": True,
                    "bypass_login": True,
                }
            },
            "format": "best[ext=mp4]/best",
            "sleep_interval": 2,
        }
    
    def _get_youtube_no_cookies_android_tv_options(self) -> dict:
        """YouTube Android TV without cookies - most reliable (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_tv"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "com.google.android.tv.youtube/4.40.30 (Linux; U; Android 9; sm-t720; Build/PPR1.180610.011) gzip",
            # Explicitly disable cookies
            "cookiefile": None,
            "no_cookies": True,
        }
    
    def _get_youtube_no_cookies_testsuite_options(self) -> dict:
        """YouTube TestSuite without cookies - bypasses most restrictions (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_testsuite"],
                    "player_skip": ["configs", "webpage", "js"],
                }
            },
            "user_agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
            "http_headers": {
                "X-YouTube-Client-Name": "30",
                "X-YouTube-Client-Version": "19.09.37",
            },
            # Explicitly disable cookies
            "cookiefile": None,
            "no_cookies": True,
            "format": "best[ext=mp4]/mp4/best",
        }
    
    def _get_youtube_no_cookies_music_options(self) -> dict:
        """YouTube Music without cookies - fewer restrictions (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_music"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "com.google.android.apps.youtube.music/5.26.1 (Linux; U; Android 11; en_US) gzip",
            "http_headers": {
                "X-YouTube-Client-Name": "21",
                "X-YouTube-Client-Version": "5.26.1",
            },
            # Explicitly disable cookies
            "cookiefile": None,
            "no_cookies": True,
        }
    
    def _get_youtube_no_cookies_embedded_options(self) -> dict:
        """YouTube Embedded without cookies - works for most public videos (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["web_embedded_player"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "http_headers": {
                "Origin": "https://www.youtube.com",
                "Referer": "https://www.youtube.com/",
            },
            # Explicitly disable cookies
            "cookiefile": None,
            "no_cookies": True,
        }
    
    def _get_youtube_mweb_no_cookies_options(self) -> dict:
        """YouTube Mobile Web client - yt-dlp 2024 recommended for PO Token era."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["mweb"],
                    "player_skip": ["configs", "js"],
                }
            },
            "user_agent": "Mozilla/5.0 (Linux; Android 11; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
            "http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                "Sec-Ch-Ua-Mobile": "?1",
                "Sec-Ch-Ua-Platform": '"Android"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
            # Explicitly disable cookies - CRITICAL for 2024
            "cookiefile": None,
            "no_cookies": True,
            "format": "best[ext=mp4]/mp4/best",
            # Additional mobile web optimizations
            "age_limit": None,
            "geo_bypass": True,
        }
    
    def _get_youtube_android_testsuite_no_cookies_options(self) -> dict:
        """YouTube Android TestSuite without cookies - most reliable for 2024."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_testsuite"],
                    "player_skip": ["configs", "webpage", "js"],
                }
            },
            "user_agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
            "http_headers": {
                "X-YouTube-Client-Name": "30",
                "X-YouTube-Client-Version": "19.09.37",
            },
            "cookiefile": None,
            "no_cookies": True,
            "format": "best[ext=mp4]/mp4/best",
            "age_limit": None,
            "geo_bypass": True,
        }
    
    def _get_youtube_android_music_no_cookies_options(self) -> dict:
        """YouTube Android Music without cookies - reliable for 2024."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_music"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "com.google.android.apps.youtube.music/5.26.1 (Linux; U; Android 11; en_US) gzip",
            "http_headers": {
                "X-YouTube-Client-Name": "21",
                "X-YouTube-Client-Version": "5.26.1",
            },
            "cookiefile": None,
            "no_cookies": True,
            "age_limit": None,
        }
    
    def _get_youtube_ios_music_no_cookies_options(self) -> dict:
        """YouTube iOS Music without cookies - reliable for 2024."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["ios_music"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "com.google.ios.youtube.music/5.21 (iPhone14,3; U; CPU iOS 15_6 like Mac OS X)",
            "http_headers": {
                "X-YouTube-Client-Name": "26",
                "X-YouTube-Client-Version": "5.21",
            },
            "cookiefile": None,
            "no_cookies": True,
            "age_limit": None,
        }
    
    def _get_youtube_web_embedded_no_cookies_options(self) -> dict:
        """YouTube Web Embedded without cookies - good for public content."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["web_embedded_player"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "http_headers": {
                "Origin": "https://www.youtube.com",
                "Referer": "https://www.youtube.com/",
            },
            "cookiefile": None,
            "no_cookies": True,
            "age_limit": None,
        }
    
    def _get_youtube_android_creator_options(self) -> dict:
        """YouTube Android Creator - for content creators."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_creator"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "com.google.android.apps.youtube.creator/22.30.100 (Linux; U; Android 11; en_US) gzip",
            "http_headers": {
                "X-YouTube-Client-Name": "14",
                "X-YouTube-Client-Version": "22.30.100",
            },
            "cookiefile": None,
            "no_cookies": True,
        }
    
    def _get_youtube_web_creator_options(self) -> dict:
        """YouTube Web Creator - for content creators."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["web_creator"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "http_headers": {
                "X-YouTube-Client-Name": "62",
                "X-YouTube-Client-Version": "1.0",
            },
            "cookiefile": None,
            "no_cookies": True,
        }
    
    def _get_youtube_tvhtml5_no_cookies_options(self) -> dict:
        """YouTube TV HTML5 without cookies - for smart TV access."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["tvhtml5_simply_embedded_player"],
                    "player_skip": ["configs", "js"],
                }
            },
            "user_agent": "Mozilla/5.0 (SMART-TV; LINUX; Tizen 6.0) AppleWebKit/537.36 (KHTML, like Gecko) 85.0.4183.93/6.0 TV Safari/537.36",
            "http_headers": {
                "X-YouTube-Client-Name": "85",
                "X-YouTube-Client-Version": "2.0",
            },
            "cookiefile": None,
            "no_cookies": True,
            "format": "best[ext=mp4]/mp4/best",
        }
    
    def _get_youtube_android_vr_no_cookies_options(self) -> dict:
        """YouTube Android VR client - highly effective at bypassing bot detection (2024)."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_vr"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "com.google.android.apps.youtube.vr.oculus/1.2.28 (Linux; U; Android 7.1.2) gzip",
            "http_headers": {
                "X-YouTube-Client-Name": "28",
                "X-YouTube-Client-Version": "1.2.28",
            },
            "cookiefile": None,
            "no_cookies": True,
            "age_limit": None,
            "geo_bypass": True,
            "format": "best[ext=mp4]/mp4/best",
        }
    
    def _get_youtube_android_producer_options(self) -> dict:
        """YouTube Android Producer client - for content creators."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_producer"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "com.google.android.apps.youtube.producer/0.20.16 (Linux; U; Android 11; en_US) gzip",
            "http_headers": {
                "X-YouTube-Client-Name": "91",
                "X-YouTube-Client-Version": "0.20.16",
            },
            "cookiefile": None,
            "no_cookies": True,
            "age_limit": None,
        }
    
    def _get_youtube_android_unplugged_options(self) -> dict:
        """YouTube TV Android Unplugged client - for YouTube TV content."""
        return {
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_unplugged"],
                    "player_skip": ["configs"],
                }
            },
            "user_agent": "com.google.android.apps.youtube.unplugged/6.36 (Linux; U; Android 9; SM-G965F Build/PPR1.180610.011) gzip",
            "http_headers": {
                "X-YouTube-Client-Name": "29",
                "X-YouTube-Client-Version": "6.36",
            },
            "cookiefile": None,
            "no_cookies": True,
            "age_limit": None,
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
            # Explicitly disable cookies for generic fallback
            "cookiefile": None,
            "no_cookies": True,
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
