#!/bin/bash

# Video Downloader API - Development Server Runner

echo "🚀 Starting Video Downloader API..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p downloads static logs cookies

# Start the server
echo "🌐 Starting FastAPI server on http://localhost:8888"
echo "📖 API docs available at http://localhost:8888/docs"
echo "🔍 Health check at http://localhost:8888/api/v1/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python scripts/run_dev.py
