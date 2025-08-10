# Video Downloader API Documentation

## Overview

The Video Downloader API is a FastAPI-based service that allows users to download videos from various platforms including YouTube, TikTok, Instagram, Twitter, Facebook, Vimeo, and more.

## Base URL

```
http://localhost:8888
```

## API Endpoints

### 1. Root Endpoint

**GET** `/`

Returns basic information about the API.

**Response:**
```json
{
  "message": "Video Downloader API",
  "version": "2.1.0",
  "features": [
    "Timestamped downloads",
    "Automatic cleanup after 5 hours",
    "Enhanced error handling",
    "Multiple platform support"
  ],
  "endpoints": {
    "POST /api/v1/download": "Initiate video download",
    "GET /api/v1/status/{task_id}": "Check download status",
    "GET /api/v1/download/{task_id}": "Download completed video",
    "GET /api/v1/cleanup": "Manually trigger cleanup",
    "GET /api/v1/health": "Health check",
    "GET /api/v1/logs": "View logs"
  }
}
```

### 2. Health Check

**GET** `/api/v1/health`

Returns the health status of the service.

**Response:**
```json
{
  "status": "healthy",
  "scheduler_status": "running",
  "downloads_directory_accessible": true,
  "current_files_count": 0,
  "cleanup_enabled": true,
  "version": "2.1.0"
}
```

### 3. Initiate Download

**POST** `/api/v1/download`

Initiates a video download from a supported platform.

**Request Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "download_type": "single",
  "quality": "720p"
}
```

**Parameters:**
- `url` (required): The video URL to download
- `download_type` (optional): Type of download (`single`, `playlist`, `album`). Default: `single`
- `quality` (optional): Video quality (`360p`, `480p`, `720p`, `1080p`, `1440p`, `best`). Default: `720p`

**Response:**
```json
{
  "task_id": "b1d90808-e764-4d01-b76f-025e6279dc90",
  "status": "initiated",
  "message": "Single download initiated (720p) for: https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "download_type": "single",
  "quality": "720p",
  "download_url": null,
  "expires_at": "2025-08-07T01:21:30.068627"
}
```

### 4. Check Download Status

**GET** `/api/v1/status/{task_id}`

Returns the current status of a download task.

**Response:**
```json
{
  "task_id": "b1d90808-e764-4d01-b76f-025e6279dc90",
  "status": "completed",
  "message": "Video downloaded successfully: Rick Astley - Never Gonna Give You Up",
  "download_type": "single",
  "quality": "720p",
  "download_url": "/api/v1/download/b1d90808-e764-4d01-b76f-025e6279dc90",
  "filename": "b1d90808-e764-4d01-b76f-025e6279dc90_20250806_202130_Rick Astley - Never Gonna Give You Up.mp4",
  "title": "Rick Astley - Never Gonna Give You Up",
  "duration": 213,
  "format": "mp4",
  "thumbnail": "https://i.ytimg.com/vi_webp/dQw4w9WgXcQ/maxresdefault.webp",
  "expires_at": "2025-08-07T01:22:19.134497",
  "created_at": "2025-08-06T20:22:19.134498"
}
```

### 5. Download File

**GET** `/api/v1/download/{task_id}`

Downloads the completed video file.

**Response:** Binary file download

### 6. Manual Cleanup

**GET** `/api/v1/cleanup`

Manually triggers cleanup of old files.

**Response:**
```json
{
  "status": "success",
  "message": "Cleanup completed successfully"
}
```

### 7. View Logs

**GET** `/api/v1/logs`

Returns information about available log files.

**Response:**
```json
{
  "logs_directory": "/app/logs",
  "available_logs": [
    {
      "filename": "video_downloader.log",
      "size_bytes": 123602,
      "modified": "2025-08-06T20:23:01.707221",
      "url": "/api/v1/logs/video_downloader.log"
    }
  ],
  "total_files": 1
}
```

### 8. Get Log File Content

**GET** `/api/v1/logs/{filename}?lines=100`

Returns the content of a specific log file.

**Parameters:**
- `lines` (optional): Number of lines to return from the end of the file. Default: 100

**Response:**
```json
{
  "filename": "video_downloader.log",
  "total_lines": 510,
  "returned_lines": 100,
  "requested_lines": 100,
  "content": "..."
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid URL format. Please check the URL and try again."
}
```

### 404 Not Found
```json
{
  "detail": "Task not found"
}
```

### 410 Gone
```json
{
  "detail": "File has been automatically deleted after 5 hours expiration period"
}
```

### 500 Internal Server Error
```json
{
  "detail": "An error occurred while processing your request."
}
```

## Supported Platforms

- YouTube (youtube.com, youtu.be)
- TikTok (tiktok.com)
- Instagram (instagram.com)
- Twitter/X (twitter.com, x.com)
- Facebook (facebook.com, fb.watch)
- Vimeo (vimeo.com)
- Dailymotion (dailymotion.com)
- Twitch (twitch.tv)

## Quality Options

- `360p`: Low quality
- `480p`: Medium quality
- `720p`: High quality (default)
- `1080p`: Very high quality
- `1440p`: Ultra quality
- `best`: Best available quality

## Download Types

- `single`: Download a single video
- `playlist`: Download an entire playlist
- `album`: Download an album (for music platforms)

## Rate Limits

Currently, there are no rate limits implemented. However, it's recommended to:

- Not exceed 10 concurrent downloads per user
- Wait at least 1 second between requests
- Respect the platform's terms of service

## Authentication

Currently, the API does not require authentication. However, for production use, it's recommended to implement:

- API key authentication
- Rate limiting
- User quotas
- Request logging

## File Expiration

Downloaded files are automatically deleted after 5 hours to conserve storage space. The cleanup process runs every 30 minutes.

## Logging

The API provides comprehensive logging:

- `video_downloader.log`: General application logs
- `errors.log`: Error-only logs

Logs can be accessed via the `/api/v1/logs` endpoint. 