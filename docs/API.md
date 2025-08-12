# Video Downloader API Documentation

## Overview

The Video Downloader API is a FastAPI-based service that allows users to download videos from various platforms including YouTube, TikTok, Instagram, and Twitter. The service includes automatic file cleanup, status tracking, and download management.

## Base URL

```
http://localhost:8888/api/v1
```

## API Endpoints

### 1. Health Check

**GET** `/health`

Returns the health status of the service.

**Response:**
```json
{
  "status": "healthy",
  "scheduler_status": "running",
  "downloads_directory_accessible": true,
  "current_files_count": 12,
  "cleanup_enabled": true,
  "version": "2.1.0"
}
```

### 2. Initiate Download

**POST** `/download`

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
- `download_type` (optional): Type of download (`single`). Default: `single`
- `quality` (optional): Video quality (`720p`, `1080p`, `best`). Default: `720p`

**Response:**
```json
{
  "task_id": "40ecfc31-e838-4b9e-98c5-df7ad99801b7",
  "status": "initiated",
  "message": "Single download initiated (720p) for: https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "download_type": "single",
  "quality": "720p",
  "download_url": null,
  "expires_at": "2025-08-12T05:54:42.742824",
  "created_at": "2025-08-12T00:54:42.742833"
}
```

### 3. Check Download Status

**GET** `/status/{task_id}`

Returns the current status of a download task.

**Response:**
```json
{
  "task_id": "40ecfc31-e838-4b9e-98c5-df7ad99801b7",
  "status": "completed",
  "message": "Video downloaded successfully",
  "download_type": "single",
  "quality": "720p",
  "download_url": "/api/v1/download/40ecfc31-e838-4b9e-98c5-df7ad99801b7",
  "filename": "40ecfc31-e838-4b9e-98c5-df7ad99801b7_20250812_005442_Rick Astley - Never Gonna Give You Up.mp4",
  "title": "Rick Astley - Never Gonna Give You Up",
  "format": "mp4",
  "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
  "expires_at": "2025-08-12T05:54:42.742824",
  "created_at": "2025-08-12T00:54:42.742833"
}
```

### 4. Download File

**GET** `/download/{task_id}`

Downloads the completed video file.

**Response:** 
- Success: Video file download (video/mp4)
- Error: Appropriate HTTP error status with message

### Error Responses

#### 400 Bad Request
```json
{
  "detail": "Invalid URL format. Please check the URL and try again."
}
```

#### 404 Not Found
```json
{
  "detail": "Task not found"
}
```

#### 410 Gone
```json
{
  "detail": "Download has expired"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Failed to initiate download: {error message}"
}
```

## Supported Platforms

The API currently supports video downloads from:
- YouTube (fully supported)
- TikTok (requires cookies for some videos)
- Instagram (requires authentication cookies)
- Twitter (requires cookies for some videos)

## File Management

- Downloads expire after 5 hours
- Automatic cleanup of expired files runs every 30 minutes
- Files are stored with unique task IDs and timestamps
- Downloads are processed in background tasks

## Docker Support

The API can be run using Docker with the following commands:

```bash
# Build the Docker image
make docker-build

# Run the container
make docker-run

# Stop the container
make docker-stop

# Clean up Docker resources
make docker-clean
```

## Cookie Management

Cookie files for various platforms should be placed in the `/cookies` directory:
- `youtube.com_cookies.txt`
- `instagram.com_cookies.txt`
- `tiktok.com_cookies.txt`
- `twitter.com_cookies.txt`

Cookies are required for some platforms to access private or restricted content.
