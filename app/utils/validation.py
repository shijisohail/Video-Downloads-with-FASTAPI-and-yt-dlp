"""
Validation utilities for URLs and platform detection.
"""

import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)

def is_valid_url(url: str) -> bool:
    """Check if URL is valid."""
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

def validate_url_platform(url: str) -> Dict[str, any]:
    """Validate if the URL is from a supported platform."""
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

def categorize_error(error_message: str) -> Dict[str, str]:
    """Categorize error messages for better user feedback."""
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
    elif "network" in error_lower or "timeout" in error_lower or "connection" in error_lower:
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