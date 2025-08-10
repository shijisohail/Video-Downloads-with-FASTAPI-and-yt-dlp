#!/usr/bin/env python3
"""
Cookie setup script for the Video Downloader API.
"""

import os
import sys
from pathlib import Path

def main():
    """Setup cookie files for different platforms."""
    project_root = Path(__file__).parent.parent
    cookies_dir = project_root / "cookies"
    
    # Ensure cookies directory exists
    cookies_dir.mkdir(exist_ok=True)
    
    # Platform cookie file templates
    platforms = {
        "youtube": "youtube.com_cookies.txt",
        "instagram": "instagram.com_cookies.txt", 
        "tiktok": "tiktok.com_cookies.txt",
        "twitter": "twitter.com_cookies.txt",
        "facebook": "facebook.com_cookies.txt",
        "vimeo": "vimeo.com_cookies.txt"
    }
    
    print("🍪 Cookie Setup for Video Downloader API")
    print("=" * 50)
    print()
    print("This script will help you set up cookie files for better download success rates.")
    print("Cookie files should be in Netscape format.")
    print()
    
    for platform, filename in platforms.items():
        cookie_file = cookies_dir / filename
        
        if cookie_file.exists():
            size = cookie_file.stat().st_size
            if size > 0:
                print(f"✅ {platform.title()}: {filename} (exists, {size} bytes)")
            else:
                print(f"⚠️  {platform.title()}: {filename} (exists but empty)")
        else:
            print(f"❌ {platform.title()}: {filename} (missing)")
    
    print()
    print("📝 Instructions:")
    print("1. Export cookies from your browser using extensions like:")
    print("   - Chrome: 'EditThisCookie' or 'Cookie Editor'")
    print("   - Firefox: 'Cookie Quick Manager'")
    print("2. Save cookies in Netscape format (.txt)")
    print("3. Place the files in the 'cookies/' directory")
    print("4. Restart the application")
    print()
    print("🔗 Cookie Export Tutorials:")
    print("- YouTube: https://github.com/ytdl-org/youtube-dl#how-do-i-pass-cookies-to-youtube-dl")
    print("- Instagram: Use browser developer tools to export cookies")
    print("- TikTok: Use browser extensions to export cookies")
    print()
    print("📁 Cookie files location:", cookies_dir.absolute())

if __name__ == "__main__":
    main() 