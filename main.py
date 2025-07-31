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

app = FastAPI(title="Video Downloader API", version="2.0.0")

# Mount static files for serving downloads
app.mount("/static", StaticFiles(directory="static"), name="static")

# Directory to store downloaded videos
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

# In-memory storage for download status (in production, use a database)
download_status = {}

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
        format_string = f'best[ext=mp4][height={quality}]/best[ext=mp4]/mp4[height={quality}]/mp4/best[height={quality}]/best'

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
        download_status[task_id].update({
            'status': 'failed',
            'message': f'Download failed: {str(e)}'
        })

@app.post("/download", response_model=DownloadResponse)
async def initiate_download(request: VideoDownloadRequest, background_tasks: BackgroundTasks):
    """Initiate video download from provided URL"""
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Initialize download status immediately (no validation to speed up response)
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
    background_tasks.add_task(download_video, str(request.url), task_id, request.download_type.value, request.quality.value)
    
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
