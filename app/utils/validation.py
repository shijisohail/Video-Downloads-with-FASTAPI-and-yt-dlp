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

    # Instagram specific errors
    if "instagram sent an empty media response" in error_lower:
        return {
            "category": "INSTAGRAM_AUTH_ERROR",
            "user_message": "Instagram requires authentication to access this content. Please provide fresh cookies or try again later.",
            "suggestion": "This Instagram post may be private or require login. Try using browser cookies or a public post.",
        }
    elif "instagram" in error_lower and "unable to extract data" in error_lower:
        return {
            "category": "INSTAGRAM_EXTRACTION_ERROR",
            "user_message": "Unable to extract Instagram content. The post may be private or deleted.",
            "suggestion": "Ensure the Instagram URL is correct and the post is publicly accessible.",
        }
    # Facebook specific errors
    elif "facebook" in error_lower and "cannot parse data" in error_lower:
        return {
            "category": "FACEBOOK_PARSE_ERROR",
            "user_message": "Unable to parse Facebook video data. The video may be private or deleted.",
            "suggestion": "Ensure the Facebook video is publicly accessible and the URL is correct.",
        }
    elif "facebook" in error_lower and "no video formats found" in error_lower:
        return {
            "category": "FACEBOOK_FORMAT_ERROR",
            "user_message": "No downloadable video formats found on Facebook. The content may be protected.",
            "suggestion": "This Facebook video may not be downloadable due to privacy settings.",
        }
    elif "unsupported url" in error_lower and "facebook" in error_lower:
        return {
            "category": "FACEBOOK_URL_ERROR",
            "user_message": "This Facebook URL format is not supported. Please use a direct video URL.",
            "suggestion": "Try using a direct Facebook video URL instead of a profile or page URL.",
        }
    # TikTok specific errors
    elif "tiktok" in error_lower and "ip address is blocked" in error_lower:
        return {
            "category": "TIKTOK_BLOCKED",
            "user_message": "TikTok has blocked access from your IP address. This is a temporary restriction.",
            "suggestion": "TikTok may have rate-limited your IP. Try again later or use a different network.",
        }
    # YouTube specific errors
    elif "youtube" in error_lower and "video unavailable" in error_lower:
        return {
            "category": "YOUTUBE_UNAVAILABLE",
            "user_message": "YouTube video is unavailable. It may be private, deleted, or region-restricted.",
            "suggestion": "Check if the YouTube video exists and is publicly accessible.",
        }
    elif "youtube" in error_lower and ("sign in" in error_lower or "confirm your age" in error_lower):
        return {
            "category": "YOUTUBE_AGE_VERIFICATION",
            "user_message": "This YouTube video requires age verification or sign-in to access.",
            "suggestion": "This video has age restrictions or privacy settings. The system will try alternative extraction methods.",
        }
    elif "youtube" in error_lower and "members-only" in error_lower:
        return {
            "category": "YOUTUBE_MEMBERS_ONLY",
            "user_message": "This YouTube video is available to channel members only.",
            "suggestion": "This content requires a YouTube channel membership to access.",
        }
    elif "youtube" in error_lower and ("premieres" in error_lower or "premiere" in error_lower):
        return {
            "category": "YOUTUBE_PREMIERE",
            "user_message": "This YouTube video is scheduled as a premiere and not yet available.",
            "suggestion": "Wait for the premiere to start or check the scheduled time.",
        }
    elif "youtube" in error_lower and "player_client" in error_lower:
        return {
            "category": "YOUTUBE_CLIENT_ERROR", 
            "user_message": "YouTube client configuration error. Trying alternative methods.",
            "suggestion": "The system is attempting different extraction strategies automatically.",
        }
    # Browser cookie errors
    elif "secretstorage not available" in error_lower:
        return {
            "category": "MISSING_DEPENDENCY",
            "user_message": "Browser cookie extraction is not available. Using fallback method.",
            "suggestion": "The system will try alternative extraction methods automatically.",
        }
    # General error patterns
    elif "private" in error_lower or "unavailable" in error_lower:
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
