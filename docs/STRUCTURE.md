# Project Structure Documentation

## Overview

This document describes the structure and organization of the Video Downloader API project. The project is organized in a modular way to separate concerns and make the codebase maintainable and scalable.

## Directory Structure

```
video_downloader_api/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entry point
│   ├── api/                     # API layer
│   │   ├── endpoints/           # API endpoints
│   │   │   ├── download.py      # Download endpoints
│   │   │   └── health.py       # Health check endpoint
│   │   └── middleware/         # API middleware
│   ├── core/                    # Core application components
│   │   ├── config.py           # Configuration settings
│   │   ├── storage.py          # Download status storage
│   │   └── scheduler.py        # Cleanup scheduler
│   ├── models/                  # Data models
│   │   ├── __init__.py
│   │   └── download.py         # Download request/response models
│   ├── services/               # Business logic services
│   │   ├── download.py        # Video download service
│   │   └── cleanup.py         # File cleanup service
│   └── utils/                  # Utility functions
│       ├── browser.py         # Cookie management
│       └── validation.py      # URL validation
├── cookies/                    # Platform-specific cookies
│   ├── youtube.com_cookies.txt
│   ├── instagram.com_cookies.txt
│   ├── tiktok.com_cookies.txt
│   └── twitter.com_cookies.txt
├── downloaded_videos/          # Download directories
│   ├── downloads/             # Completed downloads
│   └── fresh_downloads/       # Temporary download location
├── logs/                      # Application logs
│   ├── cleanup.log           # Cleanup service logs
│   └── video_downloader.log  # Main application logs
├── scripts/                   # Utility scripts
│   ├── run_cleanup.py        # Manual cleanup trigger
│   ├── run_dev.py           # Development server
│   └── run_prod.py          # Production server
├── static/                   # Static files
├── tests/                    # Test suite
├── Dockerfile               # Docker configuration
├── Makefile                # Build and run commands
├── requirements.txt        # Python dependencies
└── start.sh               # Container startup script
```

## Component Details

### API Layer (`app/api/`)
- `endpoints/download.py`: Handles video download requests and status checks
- `endpoints/health.py`: Service health monitoring

### Core (`app/core/`)
- `config.py`: Application configuration and settings
- `storage.py`: In-memory storage for download status
- `scheduler.py`: Automatic cleanup scheduling

### Models (`app/models/`)
- `download.py`: Pydantic models for request/response validation

### Services (`app/services/`)
- `download.py`: Video download implementation using yt-dlp
- `cleanup.py`: Automatic file cleanup implementation

### Utils (`app/utils/`)
- `browser.py`: Cookie management and extraction
- `validation.py`: URL and platform validation

## Docker Support

The application is containerized with the following key files:
- `Dockerfile`: Multi-stage build configuration
- `start.sh`: Container entrypoint script
- `Makefile`: Docker build and run commands

## Directory Purposes

### `/downloaded_videos`
- `downloads/`: Stores completed video downloads
- `fresh_downloads/`: Temporary storage during download

### `/cookies`
Platform-specific cookie files for authentication:
- `youtube.com_cookies.txt`: YouTube authentication
- `instagram.com_cookies.txt`: Instagram authentication
- `tiktok.com_cookies.txt`: TikTok authentication
- `twitter.com_cookies.txt`: Twitter authentication

### `/logs`
Application logging:
- `cleanup.log`: Cleanup service activity
- `video_downloader.log`: Main application logs

## Build and Run

The project includes several ways to run the application:
1. Development: `python scripts/run_dev.py`
2. Production: `python scripts/run_prod.py`
3. Docker: Use Makefile commands
   - `make docker-build`
   - `make docker-run`
   - `make docker-stop`
   - `make docker-clean`
