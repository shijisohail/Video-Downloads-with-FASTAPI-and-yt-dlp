#!/bin/bash

# Video Downloader API startup script
set -e

echo "🚀 Starting Video Downloader API Docker Container"
echo "================================================="

# Start D-Bus for secretstorage support
echo "🔧 Starting D-Bus..."
service dbus start 2>/dev/null || echo "⚠️  D-Bus already running or not available"

# Start Xvfb for headless browser support
echo "🖥️  Starting Xvfb for headless browser support..."
Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
export DISPLAY=:99

# Create necessary directories with proper permissions
echo "📁 Setting up directories..."
mkdir -p /app/downloads /app/logs /app/cookies /app/static
chown -R appuser:appuser /app/downloads /app/logs /app/cookies /app/static

# Start cron as root
echo "⏰ Starting cron daemon..."
/usr/sbin/cron

# Check if yt-dlp is working
echo "🔍 Testing yt-dlp installation..."
su appuser -c "python -c 'import yt_dlp; print(f\"yt-dlp version: {yt_dlp.version.__version__}\")'" 

# Setup cookies and extraction configurations automatically
echo "🍪 Setting up authentication cookies and extraction configs..."
su appuser -c "cd /app && python scripts/auto_setup_cookies.py server" || echo "⚠️  Cookie setup failed, continuing with defaults"

# Start the FastAPI application as appuser
echo "🚀 Starting FastAPI application as appuser..."
echo "   API will be available at: http://localhost:8888"
echo "   API Documentation: http://localhost:8888/docs"
echo "   Health Check: http://localhost:8888/api/v1/health"
echo ""

exec su appuser -c "cd /app && python -m uvicorn app.main:app --host 0.0.0.0 --port 8888 --access-log --log-level info"

