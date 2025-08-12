#!/usr/bin/env python3
"""
Enhanced cookie management script for video downloader.
This script helps extract and manage cookies for different platforms.
"""

import os
import sys
import logging
from pathlib import Path
import tempfile
import shutil

# Add app to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

try:
    import yt_dlp
    from app.utils.browser import detect_browsers, extract_cookies_from_browser
    from app.core.config import settings
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_cookies_directory():
    """Ensure cookies directory exists."""
    cookies_dir = settings.COOKIE_DIR
    cookies_dir.mkdir(exist_ok=True)
    logger.info(f"Cookies directory: {cookies_dir}")
    return cookies_dir

def extract_browser_cookies(platform: str):
    """Extract cookies from browser for a specific platform."""
    logger.info(f"Extracting {platform} cookies from browser...")
    
    available_browsers = detect_browsers()
    if not available_browsers:
        logger.warning("No browsers detected for cookie extraction")
        return False
    
    cookie_file = extract_cookies_from_browser(platform, available_browsers)
    if cookie_file:
        # Move to permanent location
        cookies_dir = setup_cookies_directory()
        permanent_path = cookies_dir / f"{platform}.com_cookies.txt"
        
        try:
            shutil.move(cookie_file, permanent_path)
            logger.info(f"Successfully extracted {platform} cookies to {permanent_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save {platform} cookies: {e}")
            return False
    else:
        logger.warning(f"Failed to extract {platform} cookies")
        return False

def create_sample_cookie_files():
    """Create sample cookie files with instructions."""
    cookies_dir = setup_cookies_directory()
    
    platforms = ['youtube', 'instagram', 'tiktok', 'facebook', 'twitter', 'vimeo']
    
    for platform in platforms:
        cookie_file = cookies_dir / f"{platform}.com_cookies.txt"
        if not cookie_file.exists():
            with open(cookie_file, 'w') as f:
                f.write(f"# {platform.title()} cookies file\n")
                f.write(f"# To use this file, export your {platform} cookies from your browser\n")
                f.write(f"# and replace this content with the cookie data.\n")
                f.write(f"# Format: Netscape HTTP Cookie File\n")
                f.write(f"# This file can be used by yt-dlp for authentication\n")
                f.write("\n")
            logger.info(f"Created sample cookie file: {cookie_file}")

def test_cookie_extraction():
    """Test cookie extraction functionality."""
    logger.info("Testing cookie extraction functionality...")
    
    # Test platforms
    platforms = ['youtube', 'instagram', 'tiktok', 'facebook']
    
    for platform in platforms:
        logger.info(f"\nTesting {platform} cookie extraction...")
        success = extract_browser_cookies(platform)
        if success:
            logger.info(f"✓ {platform} cookies extracted successfully")
        else:
            logger.warning(f"✗ {platform} cookie extraction failed")

def list_existing_cookies():
    """List existing cookie files."""
    cookies_dir = setup_cookies_directory()
    
    logger.info("\nExisting cookie files:")
    cookie_files = list(cookies_dir.glob("*.txt"))
    
    if cookie_files:
        for cookie_file in cookie_files:
            size = cookie_file.stat().st_size
            status = "Valid" if size > 100 else "Empty/Invalid"
            logger.info(f"  {cookie_file.name}: {size} bytes ({status})")
    else:
        logger.info("  No cookie files found")

def main():
    """Main function."""
    print("=== Enhanced Cookie Setup for Video Downloader API ===")
    print()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "extract":
            if len(sys.argv) > 2:
                platform = sys.argv[2].lower()
                extract_browser_cookies(platform)
            else:
                test_cookie_extraction()
        elif command == "list":
            list_existing_cookies()
        elif command == "setup":
            create_sample_cookie_files()
            list_existing_cookies()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python setup_cookies.py [extract|list|setup] [platform]")
    else:
        # Interactive mode
        while True:
            print("\nCookie Management Options:")
            print("1. List existing cookies")
            print("2. Extract cookies from browser")
            print("3. Create sample cookie files")
            print("4. Test cookie extraction")
            print("5. Exit")
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                list_existing_cookies()
            elif choice == "2":
                platform = input("Enter platform (youtube/instagram/tiktok/facebook): ").lower()
                if platform in ['youtube', 'instagram', 'tiktok', 'facebook', 'twitter', 'vimeo']:
                    extract_browser_cookies(platform)
                else:
                    print("Invalid platform")
            elif choice == "3":
                create_sample_cookie_files()
            elif choice == "4":
                test_cookie_extraction()
            elif choice == "5":
                print("Goodbye!")
                break
            else:
                print("Invalid choice")

if __name__ == "__main__":
    main()

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