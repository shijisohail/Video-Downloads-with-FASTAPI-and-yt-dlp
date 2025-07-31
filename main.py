import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional
import yt_dlp
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from enum import Enum
import aiofiles
import re

app = FastAPI(title="Video Downloader API", version="2.0.0")

# Mount static files for serving downloads
app.mount("/static", StaticFiles(directory="static"), name="static")

# Directory to store downloaded videos
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

# In-memory storage for download status (in production, use a database)
download_status = {}

# Error handling functions
def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'  # domain
        r'(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # host
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(url_pattern.match(url))

def categorize_error(error_message: str) -> dict:
    """Categorize error messages for better user feedback"""
    error_lower = error_message.lower()
    
    if 'private' in error_lower or 'unavailable' in error_lower:
        return {
            'category': 'PRIVATE_VIDEO',
            'user_message': 'This video is private or unavailable. Please check if the video is publicly accessible.',
            'suggestion': 'Try a different video URL or contact the video owner.'
        }
    
    elif 'geo' in error_lower or 'region' in error_lower or 'country' in error_lower:
        return {
            'category': 'GEO_RESTRICTED',
            'user_message': 'This video is not available in your region due to geographical restrictions.',
            'suggestion': 'This content may be restricted in your location.'
        }
    
    elif 'age' in error_lower or 'restricted' in error_lower:
        return {
            'category': 'AGE_RESTRICTED',
            'user_message': 'This video is age-restricted and cannot be downloaded.',
            'suggestion': 'Age-restricted content requires special authentication.'
        }
    
    elif 'copyright' in error_lower or 'dmca' in error_lower:
        return {
            'category': 'COPYRIGHT',
            'user_message': 'This video is protected by copyright and cannot be downloaded.',
            'suggestion': 'Please respect copyright restrictions.'
        }
    
    elif 'format' in error_lower or 'no video' in error_lower:
        return {
            'category': 'FORMAT_ERROR',
            'user_message': 'No suitable video format found for download.',
            'suggestion': 'Try selecting a different quality or check if the video supports downloads.'
        }
    
    elif 'network' in error_lower or 'timeout' in error_lower or 'connection' in error_lower:
        return {
            'category': 'NETWORK_ERROR',
            'user_message': 'Network error occurred while downloading the video.',
            'suggestion': 'Please check your internet connection and try again.'
        }
    
    elif 'not found' in error_lower or '404' in error_lower:
        return {
            'category': 'VIDEO_NOT_FOUND',
            'user_message': 'Video not found. The URL may be incorrect or the video may have been deleted.',
            'suggestion': 'Please verify the URL and try again.'
        }
    
    elif 'live' in error_lower or 'stream' in error_lower:
        return {
            'category': 'LIVE_STREAM',
            'user_message': 'Live streams cannot be downloaded while they are active.',
            'suggestion': 'Wait for the stream to end or try downloading a recorded version.'
        }
    
    elif 'login' in error_lower or 'authentication' in error_lower:
        return {
            'category': 'AUTH_REQUIRED',
            'user_message': 'This video requires authentication to access.',
            'suggestion': 'This content may require login credentials.'
        }
    
    else:
        return {
            'category': 'GENERAL_ERROR',
            'user_message': 'An error occurred while processing your request.',
            'suggestion': 'Please try again later or contact support if the issue persists.'
        }

def validate_url_platform(url: str) -> dict:
    """Validate if the URL is from a supported platform"""
    supported_patterns = {
        'youtube': [r'youtube\.com', r'youtu\.be'],
        'tiktok': [r'tiktok\.com'],
        'instagram': [r'instagram\.com'],
        'twitter': [r'twitter\.com', r'x\.com'],
        'facebook': [r'facebook\.com', r'fb\.watch'],
        'vimeo': [r'vimeo\.com'],
        'dailymotion': [r'dailymotion\.com'],
        'twitch': [r'twitch\.tv']
    }
    
    for platform, patterns in supported_patterns.items():
        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return {'supported': True, 'platform': platform}
    
    return {
        'supported': False, 
        'platform': 'unknown',
        'message': 'URL may not be from a supported platform. Supported platforms include YouTube, TikTok, Instagram, Twitter, Facebook, Vimeo, and more.'
    }

class DownloadType(str, Enum):
    SINGLE = "single"
    PLAYLIST = "playlist"
    ALBUM = "album"

class VideoQuality(str, Enum):
    LOW = "360p"          # 360p
    MEDIUM = "480p"       # 480p
    HIGH = "720p"         # 720p (default)
    VERY_HIGH = "1080p"   # 1080p
    ULTRA = "1440p"       # 1440p
    MAX = "best"          # Best available

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

def get_video_info(url: str):
    """Get video information without downloading"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 10,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
            }
        except Exception as e:
            raise Exception(f"Failed to get video info: {str(e)}")

async def download_video(url: str, task_id: str, download_type: str, quality: str):
    """Download video in background"""
    try:
        # Update status to processing
        download_status[task_id]['status'] = 'processing'
        download_status[task_id]['message'] = 'Downloading video...'
        
        # Determine format based on quality
        if quality == 'best':
            format_string = 'best[ext=mp4]/best'
        else:
            height = quality.replace('p', '')  # Remove 'p' from quality like '720p' -> '720'
            format_string = f'best[ext=mp4][height<={height}]/best[ext=mp4]/mp4[height<={height}]/mp4/best[height<={height}]/best'

        # Configure yt-dlp options for download
        filename_template = f"{task_id}_%(title)s.%(ext)s"
        ydl_opts = {
            'outtmpl': str(DOWNLOADS_DIR / filename_template),
            'format': format_string,
            'merge_output_format': 'mp4',
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': False,
            'quiet': True,
            'no_warnings': True,
            'extractflat': download_type != 'single',  # Flat playlist/album extraction for non-single
            'writethumbnail': False,
            'prefer_ffmpeg': True,
            # Additional options for better compatibility
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'referer': 'https://www.youtube.com/',
        }

        # Download the content
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if download_type == 'single':
                info = ydl.extract_info(url, download=True)
            else:
                info = ydl.extract_info(url, download=True)
                # Count total and completed files
                total_files = sum(1 for file in (info.get('entries') or []))
                completed_files = len(DOWNLOADS_DIR.glob(f"{task_id}_*"))
                download_status[task_id]['total_files'] = total_files
                download_status[task_id]['completed_files'] = completed_files

            # Find the downloaded file
            downloaded_files = list(DOWNLOADS_DIR.glob(f"{task_id}_*"))
            if not downloaded_files:
                raise Exception("Downloaded file not found")

            for downloaded_file in downloaded_files:
                # Update status for each file
                filename = downloaded_file.name
                
                # Extract video information
                video_title = info.get('title', 'Unknown Video')
                video_duration = info.get('duration', 0)
                uploader = info.get('uploader', 'Unknown')

                # Update status to completed with video info
                download_status[task_id].update({
                    'status': 'completed',
                    'message': f'Video downloaded successfully: {video_title}',
                    'download_url': f"/download/{task_id}",
                    'filename': filename,
                    'video_info': {
                        'title': video_title,
                        'duration': video_duration,
                        'uploader': uploader,
                        'original_url': url
                    }
                })

    except Exception as e:
        error_response = categorize_error(str(e))
        download_status[task_id].update({
            'status': 'failed',
            'message': error_response['user_message'],
            'error_category': error_response['category'],
            'suggestion': error_response['suggestion']
        })

@app.post("/download", response_model=DownloadResponse)
async def initiate_download(request: VideoDownloadRequest, background_tasks: BackgroundTasks):
    """Initiate video download from provided URL"""
    # Verify URL validity
    if not is_valid_url(str(request.url)):
        raise HTTPException(status_code=400, detail="Invalid URL format. Please check the URL and try again.")

    # Verify platform support
    platform_check = validate_url_platform(str(request.url))
    if not platform_check['supported']:
        raise HTTPException(status_code=400, detail=platform_check['message'])

    # Generate unique task ID
    task_id = str(uuid.uuid4())

    # Initialize download status immediately
    download_status[task_id] = {
        'task_id': task_id,
        'status': 'initiated',
        'message': f'{request.download_type.title()} download initiated ({request.quality}) for: {str(request.url)}',
        'download_type': request.download_type.value,
        'quality': request.quality.value,
        'download_url': None,
        'filename': None,
        'video_info': None,
        'total_files': None,
        'completed_files': None
    }

    # Start background download task
    try:
        background_tasks.add_task(download_video, str(request.url), task_id, request.download_type.value, request.quality.value)
    except Exception as e:
        error_response = categorize_error(str(e))
        download_status[task_id].update({
            'status': 'failed',
            'message': error_response['user_message'],
        })
        raise HTTPException(status_code=400, detail=error_response['user_message'])
    
    return DownloadResponse(
        task_id=task_id,
        status='initiated',
        message=f'{request.download_type.title()} download initiated ({request.quality}) for: {str(request.url)}',
        download_type=request.download_type.value,
        quality=request.quality.value
    )

@app.get("/status/{task_id}", response_model=DownloadStatus)
async def get_download_status(task_id: str):
    """Get download status for a specific task"""
    if task_id not in download_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return DownloadStatus(**download_status[task_id])

@app.get("/download/{task_id}")
async def download_file(task_id: str):
    """Download the completed video file"""
    if task_id not in download_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    status = download_status[task_id]
    
    if status['status'] != 'completed':
        raise HTTPException(status_code=400, detail=f"Download not completed. Status: {status['status']}")
    
    # Find the downloaded file
    downloaded_files = list(DOWNLOADS_DIR.glob(f"{task_id}_*"))
    if not downloaded_files:
        raise HTTPException(status_code=404, detail="Downloaded file not found")
    
    file_path = downloaded_files[0]
    filename = status.get('filename', file_path.name)
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/octet-stream'
    )

@app.get("/")
async def root():
    """API health check and information"""
    return {
        "message": "Video Downloader API",
        "version": "1.0.0",
        "endpoints": {
            "POST /download": "Initiate video download",
            "GET /status/{task_id}": "Check download status",
            "GET /download/{task_id}": "Download completed video"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
