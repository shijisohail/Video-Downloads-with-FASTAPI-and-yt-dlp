"""
Browser utilities for cookie extraction.
"""

import logging
import shutil
import tempfile
import os
import yt_dlp
from typing import List, Optional

logger = logging.getLogger(__name__)

def detect_browsers() -> List[str]:
    """Detect available browsers for cookie extraction."""
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

def extract_cookies_from_browser(platform: str, browsers: List[str]) -> Optional[str]:
    """Extract cookies from browser and save to temporary file."""
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