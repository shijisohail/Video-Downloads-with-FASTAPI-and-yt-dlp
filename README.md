# Video Downloader API

A comprehensive FastAPI-based video downloader service supporting multiple platforms including YouTube, TikTok, Instagram, Twitter, Facebook, Vimeo, and more.

## 🚀 Features

- **Multi-platform Support**: Download from YouTube, TikTok, Instagram, Twitter, Facebook, Vimeo, Dailymotion, Twitch
- **Quality Selection**: Choose from 360p, 480p, 720p, 1080p, 1440p, or best available quality
- **Download Types**: Single videos, playlists, and albums
- **Automatic Cleanup**: Files are automatically deleted after 5 hours
- **Background Processing**: Asynchronous download processing
- **Comprehensive Logging**: Detailed logs for monitoring and debugging
- **Health Monitoring**: Built-in health checks and status monitoring
- **Docker Support**: Ready-to-use Docker container
- **API Documentation**: Auto-generated Swagger/OpenAPI documentation

## 📁 Project Structure

```
video_downloader_api/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── api/                      # API layer
│   │   ├── __init__.py
│   │   └── endpoints/            # API endpoints
│   │       ├── __init__.py
│   │       ├── download.py       # Download endpoints
│   │       ├── status.py         # Status endpoints
│   │       ├── health.py         # Health check endpoints
│   │       ├── logs.py           # Log viewing endpoints
│   │       └── cleanup.py        # Cleanup endpoints
│   ├── core/                     # Core application components
│   │   ├── __init__.py
│   │   ├── config.py             # Configuration settings
│   │   ├── storage.py            # Storage management
│   │   └── scheduler.py          # Background task scheduler
│   ├── models/                   # Data models
│   │   ├── __init__.py
│   │   └── download.py           # Download-related models
│   ├── services/                 # Business logic services
│   │   ├── __init__.py
│   │   ├── download.py           # Download service
│   │   └── cleanup.py            # Cleanup service
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       ├── browser.py            # Browser utilities
│       └── validation.py         # Validation utilities
├── config/                       # Configuration files
│   └── logging.py                # Logging configuration
├── scripts/                      # Utility scripts
│   ├── run_dev.py                # Development server runner
│   ├── run_prod.py               # Production server runner
│   └── run_cleanup.py            # Standalone cleanup script
├── tests/                        # Test files
│   ├── __init__.py
│   └── test_api.py               # API tests
├── docs/                         # Documentation
│   └── API.md                    # API documentation
├── cookies/                      # Cookie files for platforms
├── downloads/                    # Downloaded files (created automatically)
├── logs/                         # Log files (created automatically)
├── static/                       # Static files (created automatically)
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker configuration
├── start.sh                      # Docker start script
├── run.sh                        # Development run script
└── README.md                     # This file
```

## 🛠️ Installation

### Prerequisites

- Python 3.11+
- FFmpeg
- Docker (optional)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd video_downloader_api
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the development server**
   ```bash
   python scripts/run_dev.py
   ```

### Docker Setup

1. **Build the Docker image**
   ```bash
   docker build -t video-downloader-api .
   ```

2. **Run the container**
   ```bash
   docker run -d --name video-downloader-container \
     -p 8888:8888 \
     -v $(pwd)/downloads:/app/downloads \
     -v $(pwd)/logs:/app/logs \
     video-downloader-api
   ```

## 🚀 Usage

### API Endpoints

The API is available at `http://localhost:8888` with the following endpoints:

- **GET** `/` - API information
- **GET** `/api/v1/health` - Health check
- **POST** `/api/v1/download` - Initiate download
- **GET** `/api/v1/status/{task_id}` - Check download status
- **GET** `/api/v1/download/{task_id}` - Download completed file
- **GET** `/api/v1/cleanup` - Manual cleanup trigger
- **GET** `/api/v1/logs` - View available logs
- **GET** `/api/v1/logs/{filename}` - View specific log file

### Example Usage

1. **Initiate a download**
   ```bash
   curl -X POST "http://localhost:8888/api/v1/download" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
       "download_type": "single",
       "quality": "720p"
     }'
   ```

2. **Check download status**
   ```bash
   curl "http://localhost:8888/api/v1/status/{task_id}"
   ```

3. **Download the file**
   ```bash
   curl "http://localhost:8888/api/v1/download/{task_id}" -o video.mp4
   ```

### API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8888/docs`
- ReDoc: `http://localhost:8888/redoc`

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root to customize settings:

```env
# Server settings
HOST=0.0.0.0
PORT=8888
DEBUG=false

# Cleanup settings
CLEANUP_INTERVAL_HOURS=5
CLEANUP_FREQUENCY_MINUTES=30

# Download settings
MAX_RETRIES=10
SOCKET_TIMEOUT=60
CHUNK_SIZE=10485760
```

### Cookie Files

For better download success rates, you can provide cookie files for different platforms in the `cookies/` directory:

- `cookies/youtube.com_cookies.txt` - YouTube cookies
- `cookies/instagram.com_cookies.txt` - Instagram cookies
- `cookies/tiktok.com_cookies.txt` - TikTok cookies
- `cookies/twitter.com_cookies.txt` - Twitter cookies
- `cookies/facebook.com_cookies.txt` - Facebook cookies
- `cookies/vimeo.com_cookies.txt` - Vimeo cookies

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

## 📊 Monitoring

### Health Check

Monitor the service health:

```bash
curl http://localhost:8888/api/v1/health
```

### Logs

View application logs:

```bash
# List available logs
curl http://localhost:8888/api/v1/logs

# View specific log file
curl http://localhost:8888/api/v1/logs/video_downloader.log?lines=100
```

### Metrics

The API provides basic metrics through the health endpoint:
- Scheduler status
- Downloads directory accessibility
- Current file count
- Cleanup status

## 🔒 Security Considerations

- **File Access**: Downloaded files are accessible via task IDs
- **Rate Limiting**: Consider implementing rate limiting for production
- **Authentication**: Add authentication for production deployments
- **Input Validation**: All inputs are validated before processing
- **Error Handling**: Comprehensive error handling prevents information leakage

## 🚨 Limitations

- **Platform Restrictions**: Some platforms may block automated downloads
- **File Storage**: Files are stored locally and automatically cleaned up
- **Concurrent Downloads**: No built-in limit on concurrent downloads
- **Authentication**: Some content may require platform-specific authentication

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

1. Check the API documentation at `/docs`
2. Review the logs for error details
3. Open an issue on GitHub
4. Check the troubleshooting section below

## 🔧 Troubleshooting

### Common Issues

1. **Download fails with "private video" error**
   - Ensure the video is publicly accessible
   - Try using cookie files for authentication

2. **"Platform not supported" error**
   - Check if the URL is from a supported platform
   - Verify the URL format

3. **Files not being cleaned up**
   - Check if the scheduler is running
   - Verify the cleanup interval settings
   - Check the logs for cleanup errors

4. **Docker container won't start**
   - Ensure ports are not already in use
   - Check Docker logs: `docker logs video-downloader-container`
   - Verify volume permissions

### Debug Mode

Enable debug mode for more detailed logging:

```bash
export DEBUG=true
python scripts/run_dev.py
```

### Manual Cleanup

Trigger manual cleanup:

```bash
curl http://localhost:8888/api/v1/cleanup
```
