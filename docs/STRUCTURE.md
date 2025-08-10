# Project Structure Documentation

## Overview

This document describes the organized file structure of the Video Downloader API project.

## Directory Structure

```
video_downloader_api/
├── app/                          # Main application package
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # FastAPI application entry point
│   ├── api/                     # API layer
│   │   ├── __init__.py
│   │   └── endpoints/           # API endpoints
│   │       ├── __init__.py
│   │       ├── download.py      # Download endpoints
│   │       ├── status.py        # Status endpoints
│   │       ├── health.py        # Health check endpoints
│   │       ├── logs.py          # Log viewing endpoints
│   │       └── cleanup.py       # Cleanup endpoints
│   ├── core/                    # Core application components
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration settings
│   │   ├── storage.py           # Storage management
│   │   └── scheduler.py         # Background task scheduler
│   ├── models/                  # Data models
│   │   ├── __init__.py
│   │   └── download.py          # Download-related models
│   ├── services/                # Business logic services
│   │   ├── __init__.py
│   │   ├── download.py          # Download service
│   │   └── cleanup.py           # Cleanup service
│   └── utils/                   # Utility functions
│       ├── __init__.py
│       ├── browser.py           # Browser utilities
│       └── validation.py        # Validation utilities
├── config/                      # Configuration files
│   └── logging.py               # Logging configuration
├── cookies/                     # Cookie files for platforms
│   ├── .gitkeep                 # Keep directory in git
│   ├── youtube.com_cookies.txt  # YouTube cookies
│   ├── instagram.com_cookies.txt # Instagram cookies
│   ├── tiktok.com_cookies.txt   # TikTok cookies
│   ├── twitter.com_cookies.txt  # Twitter cookies
│   ├── facebook.com_cookies.txt # Facebook cookies
│   └── vimeo.com_cookies.txt    # Vimeo cookies
├── docs/                        # Documentation
│   ├── API.md                   # API documentation
│   └── STRUCTURE.md             # This file
├── downloads/                   # Downloaded files
│   └── .gitkeep                 # Keep directory in git
├── logs/                        # Log files
│   ├── .gitkeep                 # Keep directory in git
│   ├── video_downloader.log     # General logs
│   ├── errors.log               # Error logs
│   ├── cleanup.log              # Cleanup logs
│   └── cron.log                 # Cron job logs
├── scripts/                     # Utility scripts
│   ├── run_dev.py               # Development server runner
│   ├── run_prod.py              # Production server runner
│   ├── run_cleanup.py           # Standalone cleanup script
│   └── setup_cookies.py         # Cookie setup helper
├── static/                      # Static files
│   └── .gitkeep                 # Keep directory in git
├── tests/                       # Test files
│   ├── __init__.py
│   └── test_api.py              # API tests
├── .gitignore                   # Git ignore rules
├── Dockerfile                   # Docker configuration
├── README.md                    # Project README
├── requirements.txt             # Python dependencies
├── run.sh                       # Development run script
└── start.sh                     # Docker start script
```

## Key Improvements Made

### 1. Cookie Organization
- **Before**: Cookie files were scattered in the root directory
- **After**: All cookie files are organized in the `cookies/` directory
- **Benefits**: 
  - Cleaner project structure
  - Better organization
  - Easier to manage and update cookies
  - Proper separation of concerns

### 2. Dockerfile Consolidation
- **Before**: Two Dockerfiles (`Dockerfile` and `Dockerfile.new`)
- **After**: Single, updated `Dockerfile`
- **Benefits**:
  - No confusion about which Dockerfile to use
  - Updated for new project structure
  - Proper cookie directory handling
  - Updated health check endpoint

### 3. File Cleanup
- **Removed**: Old files that are no longer needed
  - `main.py` (replaced by `app/main.py`)
  - `standalone_cleanup.py` (replaced by `scripts/run_cleanup.py`)
  - `server_local.log` and `server.log` (logs now in `logs/` directory)
  - `downloaded_video.mp4` (temporary file)
  - `Dockerfile.new` (duplicate)

### 4. Configuration Updates
- **Updated**: Configuration to point to new cookie directory
- **Added**: Cookie directory creation in startup
- **Updated**: Dockerfile to copy cookies from correct location
- **Updated**: Health check endpoint to use new API structure

### 5. Scripts and Tools
- **Added**: `scripts/setup_cookies.py` for cookie management
- **Updated**: `run.sh` to use new structure
- **Updated**: All scripts to use proper paths

## File Organization Principles

### 1. Separation of Concerns
- **API Layer**: Handles HTTP requests and responses
- **Service Layer**: Contains business logic
- **Model Layer**: Defines data structures
- **Utility Layer**: Provides helper functions

### 2. Configuration Management
- **Centralized**: All settings in `app/core/config.py`
- **Environment-aware**: Support for `.env` files
- **Flexible**: Easy to customize for different environments

### 3. Modularity
- **Independent Components**: Each module can be tested independently
- **Clear Dependencies**: Explicit import statements
- **Reusable Code**: Services can be used across different endpoints

### 4. Documentation
- **Comprehensive README**: Updated with new structure
- **API Documentation**: Detailed endpoint documentation
- **Structure Documentation**: This file for project organization

## Usage Guidelines

### 1. Adding New Endpoints
1. Create new file in `app/api/endpoints/`
2. Define router with proper tags
3. Import in `app/api/endpoints/__init__.py`
4. Add to main app in `app/main.py`

### 2. Adding New Services
1. Create new file in `app/services/`
2. Define service class with business logic
3. Import in `app/services/__init__.py`
4. Use in endpoints as needed

### 3. Adding New Models
1. Create new file in `app/models/`
2. Define Pydantic models
3. Import in `app/models/__init__.py`
4. Use in endpoints and services

### 4. Managing Cookies
1. Export cookies from browser in Netscape format
2. Place in `cookies/` directory with proper naming
3. Run `python3 scripts/setup_cookies.py` to verify
4. Restart application

### 5. Running the Application
- **Development**: `./run.sh` or `python3 scripts/run_dev.py`
- **Production**: `python3 scripts/run_prod.py`
- **Docker**: `docker build -t video-downloader-api . && docker run ...`

## Benefits of New Structure

1. **Maintainability**: Code is organized and easy to navigate
2. **Scalability**: Easy to add new features and endpoints
3. **Testability**: Services and utilities can be easily tested
4. **Deployment**: Multiple deployment options (local, Docker, production)
5. **Documentation**: Comprehensive documentation and examples
6. **Configuration**: Flexible configuration management
7. **Logging**: Enhanced logging and monitoring capabilities
8. **Cookie Management**: Organized cookie handling for better download success

## Migration Notes

If migrating from the old structure:

1. **Update imports**: All imports now use the new package structure
2. **Update configuration**: Cookie directory path has changed
3. **Update scripts**: Use new script paths
4. **Update Docker**: Use updated Dockerfile
5. **Test thoroughly**: Ensure all functionality works with new structure

The new structure follows Python and FastAPI best practices, making the codebase more professional, maintainable, and scalable. 