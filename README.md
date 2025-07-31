# Video Downloader API

A FastAPI-based service that downloads videos from URLs and provides downloadable links with comprehensive metadata extraction. Perfect for mobile applications that need to download videos from various platforms.

## Features

- **REST API**: Receive video URLs via REST endpoints
- **Asynchronous Processing**: Downloads happen in background
- **Status Tracking**: Check download progress with task IDs
- **Direct Downloads**: Generate downloadable links for completed videos
- **Multiple Platform Support**: Uses yt-dlp to support YouTube, TikTok, Instagram, Twitter, Facebook, Vimeo, and many other platforms
- **Video Metadata Extraction**: Extracts title, duration, format, thumbnail, and direct video URLs
- **Quality Selection**: Choose from 360p, 480p, 720p, 1080p, 1440p, or best available
- **Download Types**: Single video, playlist, or album downloads
- **Thumbnail Downloads**: Automatically downloads video thumbnails
- **Smart Error Handling**: Categorized error messages with helpful suggestions
- **Clean Response Format**: Metadata fields only included for successful downloads
- **Mobile-Friendly**: Designed for integration with mobile applications

## API Endpoints

### 1. Initiate Download
```http
POST /download
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "quality": "720p",
  "download_type": "single"
}
```

**Request Parameters:**
- `url` (required): Video URL from supported platforms
- `quality` (optional): Video quality - `360p`, `480p`, `720p` (default), `1080p`, `1440p`, or `best`
- `download_type` (optional): `single` (default), `playlist`, or `album`

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "initiated",
  "message": "Single download initiated (720p) for: Video Title",
  "download_type": "single",
  "quality": "720p",
  "download_url": null
}
```

### 2. Check Download Status
```http
GET /status/{task_id}
```

**Response (Completed):**
```json
{
  "task_id": "uuid-string",
  "status": "completed",
  "message": "Video downloaded successfully: Rick Astley - Never Gonna Give You Up",
  "download_type": "single",
  "quality": "720p",
  "download_url": "/download/uuid-string",
  "filename": "uuid-string_Rick Astley - Never Gonna Give You Up.mp4",
  "total_files": null,
  "completed_files": null,
  "title": "Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster)",
  "url": "https://rr3---sn-ab5sznly.googlevideo.com/videoplayback?expire=1754012202...",
  "duration": 213,
  "format": "mp4",
  "thumbnail": "https://i.ytimg.com/vi_webp/dQw4w9WgXcQ/maxresdefault.webp"
}
```

**Response (Failed):**
```json
{
  "task_id": "uuid-string",
  "status": "failed",
  "message": "This video is private or unavailable. Please check if the video is publicly accessible.",
  "download_type": "single",
  "quality": "720p",
  "download_url": null,
  "filename": null,
  "total_files": null,
  "completed_files": null
}
```

**Status values:**
- `initiated`: Download request received
- `processing`: Video is being downloaded
- `completed`: Download finished, file ready
- `failed`: Download failed

### 3. Download Video File
```http
GET /download/{task_id}
```

Returns the video file for download when status is `completed`.

### 4. Health Check
```http
GET /health
```

## Installation & Setup

### Option 1: Local Development

1. **Clone and navigate to project:**
```bash
cd video_downloader_api
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the server:**
```bash
python main.py
```

The API will be available at `http://localhost:8888`

### Option 2: Docker

1. **Build the Docker image:**
```bash
docker build -t video-downloader-api .
```

2. **Run the container:**
```bash
docker run -p 8888:8000 -v $(pwd)/downloads:/app/downloads video-downloader-api
```

## Usage Example

### Using curl:

1. **Start a download:**
```bash
curl -X POST "http://localhost:8888/download" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "quality": "720p"}'
```

2. **Check status:**
```bash
curl "http://localhost:8888/status/YOUR_TASK_ID"
```

3. **Download the file:**
```bash
curl -O "http://localhost:8888/download/YOUR_TASK_ID"
```

### Mobile App Integration:

```javascript
// 1. Initiate download
const response = await fetch('http://your-api-url/download', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    url: 'https://www.youtube.com/watch?v=VIDEO_ID'
  })
});

const { task_id } = await response.json();

// 2. Poll for completion
const checkStatus = async () => {
  const statusResponse = await fetch(`http://your-api-url/status/${task_id}`);
  const status = await statusResponse.json();
  
  if (status.status === 'completed') {
    // 3. Show download link
    const downloadUrl = `http://your-api-url/download/${task_id}`;
    showDownloadLink(downloadUrl);
  } else if (status.status === 'processing') {
    // Keep checking
    setTimeout(checkStatus, 2000);
  }
};

checkStatus();
```

## Supported Platforms

Thanks to yt-dlp, this API supports downloads from:
- YouTube
- Vimeo
- Facebook
- Instagram
- TikTok
- Twitter
- And many more platforms

## Configuration

### Video Quality
By default, videos are downloaded in 720p or lower for faster processing. You can modify this in `main.py`:

```python
ydl_opts = {
    'format': 'best[height<=1080]/best',  # Change to 1080p
    # ... other options
}
```

### Storage
Downloaded files are stored in the `downloads/` directory. In production, consider:
- Using cloud storage (AWS S3, Google Cloud Storage)
- Implementing file cleanup policies
- Adding file size limits

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation powered by Swagger UI.

## Production Considerations

1. **Database**: Replace in-memory storage with a proper database (PostgreSQL, MongoDB)
2. **File Storage**: Use cloud storage for scalability
3. **Rate Limiting**: Implement rate limiting to prevent abuse
4. **Authentication**: Add API key or JWT authentication
5. **Monitoring**: Add logging and monitoring
6. **File Cleanup**: Implement automatic cleanup of old files
7. **Error Handling**: Enhanced error handling and user feedback

## License

This project is open source and available under the MIT License.
