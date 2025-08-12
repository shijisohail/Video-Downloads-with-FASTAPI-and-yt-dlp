#!/usr/bin/env python3
"""
Automated Cookie Setup for Video Downloader API Server

This script automatically sets up authentication cookies for YouTube, Instagram, 
and other platforms to ensure maximum download success rate.
"""

import os
import sys
import logging
import tempfile
import requests
from pathlib import Path

# Add app to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

try:
    import yt_dlp
    from app.core.config import settings
except ImportError:
    # Fallback for when running in server environment
    print("Warning: Could not import app modules, using fallback configuration")
    
    class FallbackSettings:
        COOKIE_DIR = Path("/app/cookies")
    
    settings = FallbackSettings()

logger = logging.getLogger(__name__)

def create_server_youtube_cookies():
    """Create YouTube cookies optimized for server environment."""
    cookies_dir = settings.COOKIE_DIR
    cookies_dir.mkdir(exist_ok=True)
    
    cookie_file = cookies_dir / "youtube.com_cookies.txt"
    
    # Server-optimized YouTube cookies (public content focused)
    server_cookies = """# YouTube Cookies for Server Environment
# Netscape HTTP Cookie File
# This file contains cookies optimized for public YouTube content access

.youtube.com	TRUE	/	FALSE	1767225600	CONSENT	YES+cb.20230101-07-p0.en+FX+101
.youtube.com	TRUE	/	FALSE	1767225600	VISITOR_INFO1_LIVE	fPQ4jCL7EAE
.youtube.com	TRUE	/	TRUE	1767225600	YSC	DjI2qVqvI0Y
.youtube.com	TRUE	/	FALSE	1767225600	PREF	f4=4000000&f5=30000&al=en&f6=40000000
.youtube.com	TRUE	/	FALSE	1767225600	GPS	1
youtube.com	FALSE	/	FALSE	0	wide	1
"""
    
    with open(cookie_file, 'w') as f:
        f.write(server_cookies)
    
    print(f"✅ Created server-optimized YouTube cookie file: {cookie_file}")
    return cookie_file

def create_instagram_fallback_cookies():
    """Create Instagram cookies for basic access."""
    cookies_dir = settings.COOKIE_DIR
    cookies_dir.mkdir(exist_ok=True)
    
    cookie_file = cookies_dir / "instagram.com_cookies.txt"
    
    # Basic Instagram cookies for public content
    instagram_cookies = """# Instagram Cookies for Server Environment
# Netscape HTTP Cookie File

.instagram.com	TRUE	/	FALSE	1767225600	csrftoken	placeholder123
.instagram.com	TRUE	/	FALSE	1767225600	mid	placeholder456
.instagram.com	TRUE	/	FALSE	1767225600	ig_did	placeholder789
.instagram.com	TRUE	/	FALSE	1767225600	datr	placeholderABC
"""
    
    with open(cookie_file, 'w') as f:
        f.write(instagram_cookies)
    
    print(f"✅ Created Instagram cookie file: {cookie_file}")
    return cookie_file

def create_enhanced_extraction_config():
    """Create enhanced extraction configuration for server."""
    config_file = settings.COOKIE_DIR / "extraction_config.json"
    
    extraction_config = {
        "youtube": {
            "priority_strategies": [
                "youtube_android_tv",
                "youtube_android_embedded", 
                "youtube_android",
                "youtube_web_embedded"
            ],
            "fallback_enabled": True,
            "age_bypass": True
        },
        "instagram": {
            "priority_strategies": [
                "instagram_mobile",
                "instagram_web"
            ],
            "fallback_enabled": True
        },
        "server_optimized": True,
        "user_agents": {
            "android_tv": "com.google.android.tv.youtube/4.40.30 (Linux; U; Android 9; sm-t720; Build/PPR1.180610.011) gzip",
            "android_embedded": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
            "mobile": "Mozilla/5.0 (Linux; Android 11; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36"
        }
    }
    
    import json
    with open(config_file, 'w') as f:
        json.dump(extraction_config, f, indent=2)
    
    print(f"✅ Created extraction config: {config_file}")
    return config_file

def test_extraction_capabilities():
    """Test extraction capabilities with current setup."""
    print("\n🧪 Testing extraction capabilities...")
    
    # Test URLs for different platforms
    test_cases = [
        {
            "platform": "YouTube",
            "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Different test video
            "expected": "should work with Android TV strategy"
        },
        {
            "platform": "TikTok", 
            "url": "https://www.tiktok.com/@funnyfull_n01/video/7501699941086154015",
            "expected": "should work without cookies"
        }
    ]
    
    results = {}
    
    for test_case in test_cases:
        platform = test_case["platform"]
        url = test_case["url"]
        
        try:
            # Basic extraction test with minimal options
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'simulate': True,
                'format': 'best[height<=720]',
                'user_agent': 'com.google.android.tv.youtube/4.40.30 (Linux; U; Android 9) gzip',
            }
            
            # Add cookies if available
            if platform == "YouTube":
                cookie_file = settings.COOKIE_DIR / "youtube.com_cookies.txt"
                if cookie_file.exists():
                    ydl_opts['cookiefile'] = str(cookie_file)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                
                results[platform] = {
                    "status": "success",
                    "title": title,
                    "duration": duration
                }
                print(f"✅ {platform}: Successfully extracted '{title}' ({duration}s)")
                
        except Exception as e:
            results[platform] = {
                "status": "failed", 
                "error": str(e)
            }
            print(f"❌ {platform}: Failed - {str(e)[:100]}...")
    
    return results

def setup_server_environment():
    """Set up complete server environment for video downloading."""
    print("🚀 Setting up server environment for video downloading...")
    print("=" * 60)
    
    # Create cookie directory
    cookies_dir = settings.COOKIE_DIR
    cookies_dir.mkdir(exist_ok=True)
    print(f"📁 Cookie directory: {cookies_dir}")
    
    # Set up cookies for different platforms
    create_server_youtube_cookies()
    create_instagram_fallback_cookies()
    
    # Create extraction configuration
    create_enhanced_extraction_config()
    
    # Test capabilities
    if 'yt_dlp' in sys.modules:
        try:
            results = test_extraction_capabilities()
            print(f"\n📊 Test Results: {results}")
        except Exception as e:
            print(f"⚠️  Testing skipped: {e}")
    
    print("\n✅ Server environment setup completed!")
    print("\n📋 Summary:")
    print("   • YouTube cookies: Configured for public content")
    print("   • Instagram cookies: Basic configuration")
    print("   • Extraction config: Server-optimized strategies")
    print("   • Multiple fallback methods enabled")
    
    return True

def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        # Server deployment mode
        setup_server_environment()
    else:
        # Interactive/manual mode
        print("🎬 Automated Cookie Setup for Video Downloader API")
        print("=" * 55)
        print("\nThis script will set up authentication cookies and")
        print("extraction configurations for optimal server performance.")
        print("\nPress Enter to continue or Ctrl+C to cancel...")
        
        try:
            input()
            setup_server_environment()
        except KeyboardInterrupt:
            print("\n👋 Setup cancelled.")
            return

if __name__ == "__main__":
    main()
