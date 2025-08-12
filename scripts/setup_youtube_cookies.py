#!/usr/bin/env python3
"""
YouTube Cookie Setup Utility for Video Downloader API

This script helps extract and set up YouTube cookies for better download success,
especially for age-restricted or region-locked content.
"""

import os
import sys
import logging
import subprocess
import tempfile
from pathlib import Path

# Add app to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

try:
    import yt_dlp
    from app.core.config import settings
    from app.utils.browser import detect_browsers, extract_cookies_from_browser
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_sample_youtube_cookie():
    """Create a sample YouTube cookie file with instructions."""
    cookies_dir = settings.COOKIE_DIR
    cookies_dir.mkdir(exist_ok=True)
    
    cookie_file = cookies_dir / "youtube.com_cookies.txt"
    
    sample_content = """# YouTube Cookies File (Netscape HTTP Cookie File Format)
# 
# To use this file:
# 1. Install a browser extension like "EditThisCookie" (Chrome) or "Cookie Quick Manager" (Firefox)
# 2. Visit YouTube and log in to your account
# 3. Navigate to a video that normally requires sign-in or age verification
# 4. Export cookies in Netscape format and replace this content
# 
# Format: domain	flag	path	secure	expiration	name	value
# Example (DO NOT USE - this is just a template):
# .youtube.com	TRUE	/	FALSE	1735689600	CONSENT	YES+cb.20210328-17-p0.en+FX+
# .youtube.com	TRUE	/	TRUE	1735689600	LOGIN_INFO	AFmmF2swRgIhANE...
#
# For age-restricted content, make sure to include these cookies after viewing such content:
# - CONSENT
# - LOGIN_INFO  
# - VISITOR_INFO1_LIVE
# - YSC
"""
    
    with open(cookie_file, 'w') as f:
        f.write(sample_content)
    
    print(f"✅ Created sample YouTube cookie file: {cookie_file}")
    return cookie_file

def test_youtube_extraction_with_cookies():
    """Test YouTube extraction with current cookies."""
    cookies_dir = settings.COOKIE_DIR
    cookie_file = cookies_dir / "youtube.com_cookies.txt"
    
    if not cookie_file.exists() or cookie_file.stat().st_size < 200:
        print("❌ No valid YouTube cookie file found")
        return False
    
    print("🧪 Testing YouTube extraction with cookies...")
    
    # Test URLs that commonly require authentication
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Public video
        # Add more test URLs here if needed
    ]
    
    for url in test_urls:
        print(f"\n📹 Testing: {url}")
        
        ydl_opts = {
            'cookiefile': str(cookie_file),
            'quiet': True,
            'no_warnings': True,
            'simulate': True,  # Don't actually download
            'format': 'best[height<=720]',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                print(f"✅ Successfully extracted: {title} ({duration}s)")
                return True
                
        except Exception as e:
            error_msg = str(e).lower()
            if 'sign in' in error_msg or 'authentication' in error_msg:
                print(f"❌ Authentication required: {e}")
            elif 'age' in error_msg:
                print(f"❌ Age verification needed: {e}")
            else:
                print(f"❌ Extraction failed: {e}")
    
    return False

def extract_cookies_from_browser_for_youtube():
    """Extract YouTube cookies from browser."""
    print("🔍 Attempting to extract YouTube cookies from browser...")
    
    available_browsers = detect_browsers()
    if not available_browsers:
        print("❌ No browsers detected for cookie extraction")
        return False
    
    print(f"🌐 Available browsers: {', '.join(available_browsers)}")
    
    success = False
    for browser in available_browsers:
        try:
            print(f"\n📦 Trying to extract cookies from {browser}...")
            
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_cookie_file = Path(temp_dir) / "youtube_temp_cookies.txt"
                
                ydl_opts = {
                    'cookiesfrombrowser': (browser, None, None, None),
                    'cookiefile': str(temp_cookie_file),
                    'writecookiefile': True,
                    'quiet': True,
                    'no_warnings': True,
                    'simulate': True,
                }
                
                # Test extraction on YouTube homepage
                test_url = "https://www.youtube.com"
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(test_url, download=False)
                
                # Check if cookies were extracted
                if temp_cookie_file.exists() and temp_cookie_file.stat().st_size > 100:
                    # Move to permanent location
                    cookies_dir = settings.COOKIE_DIR
                    cookies_dir.mkdir(exist_ok=True)
                    permanent_cookie_file = cookies_dir / "youtube.com_cookies.txt"
                    
                    # Read and enhance the cookie content
                    with open(temp_cookie_file, 'r') as temp_f:
                        cookie_content = temp_f.read()
                    
                    # Add header comment
                    enhanced_content = f"""# YouTube cookies extracted from {browser}
# Generated on: {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}
# 
{cookie_content}
"""
                    
                    with open(permanent_cookie_file, 'w') as perm_f:
                        perm_f.write(enhanced_content)
                    
                    print(f"✅ Successfully extracted YouTube cookies from {browser}")
                    print(f"📁 Saved to: {permanent_cookie_file}")
                    success = True
                    break
                else:
                    print(f"❌ No cookies extracted from {browser}")
                    
        except Exception as e:
            print(f"❌ Failed to extract from {browser}: {e}")
            continue
    
    return success

def validate_existing_cookies():
    """Validate existing YouTube cookie file."""
    cookies_dir = settings.COOKIE_DIR
    cookie_file = cookies_dir / "youtube.com_cookies.txt"
    
    print(f"🔍 Checking existing cookie file: {cookie_file}")
    
    if not cookie_file.exists():
        print("❌ No YouTube cookie file found")
        return False
    
    file_size = cookie_file.stat().st_size
    print(f"📊 Cookie file size: {file_size} bytes")
    
    if file_size < 100:
        print("⚠️  Cookie file is too small (likely empty or template only)")
        return False
    
    # Check for essential cookie patterns
    with open(cookie_file, 'r') as f:
        content = f.read()
    
    essential_cookies = ['youtube.com', 'CONSENT', 'VISITOR_INFO1_LIVE']
    found_cookies = []
    
    for cookie_name in essential_cookies:
        if cookie_name in content:
            found_cookies.append(cookie_name)
    
    print(f"✅ Found essential cookies: {', '.join(found_cookies)}")
    
    if len(found_cookies) >= 2:
        print("✅ Cookie file looks valid")
        return True
    else:
        print("⚠️  Cookie file may be incomplete")
        return False

def main():
    """Main function."""
    print("🎬 YouTube Cookie Setup for Video Downloader API")
    print("=" * 55)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "extract":
            print("\n🔄 Extracting cookies from browser...")
            success = extract_cookies_from_browser_for_youtube()
            if success:
                print("\n🧪 Testing extraction with new cookies...")
                test_youtube_extraction_with_cookies()
            
        elif command == "test":
            print("\n🧪 Testing current cookie setup...")
            test_youtube_extraction_with_cookies()
            
        elif command == "validate":
            print("\n✅ Validating existing cookies...")
            validate_existing_cookies()
            
        elif command == "sample":
            print("\n📝 Creating sample cookie file...")
            create_sample_youtube_cookie()
            
        else:
            print(f"❌ Unknown command: {command}")
            print("Usage: python setup_youtube_cookies.py [extract|test|validate|sample]")
    
    else:
        # Interactive mode
        print("\n🛠️  YouTube Cookie Management Options:")
        print("1. 📝 Create sample cookie file with instructions")
        print("2. 🔍 Extract cookies from browser")
        print("3. ✅ Validate existing cookie file")
        print("4. 🧪 Test YouTube extraction with current cookies")
        print("5. ❌ Exit")
        
        while True:
            try:
                choice = input("\n👉 Enter your choice (1-5): ").strip()
                
                if choice == "1":
                    create_sample_youtube_cookie()
                elif choice == "2":
                    success = extract_cookies_from_browser_for_youtube()
                    if success:
                        test_youtube_extraction_with_cookies()
                elif choice == "3":
                    validate_existing_cookies()
                elif choice == "4":
                    test_youtube_extraction_with_cookies()
                elif choice == "5":
                    print("👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid choice. Please enter 1-5.")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break

if __name__ == "__main__":
    main()
