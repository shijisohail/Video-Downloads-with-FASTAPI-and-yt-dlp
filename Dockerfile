FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=UTC
ENV APP_ENV=production

# Install dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    gnupg \
    curl \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for cookie extraction
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create required directories with correct permissions
RUN mkdir -p downloaded_videos/downloads downloaded_videos/fresh_downloads logs static cookies \
    && chmod -R 755 downloaded_videos logs static cookies scripts

# Create non-root user and set permissions
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app

# Setup cleanup cron job
RUN echo "*/30 * * * * cd /app && /usr/local/bin/python3 scripts/run_cleanup.py >> /app/logs/cleanup.log 2>&1" > /etc/cron.d/cleanup-cron \
    && chmod 0644 /etc/cron.d/cleanup-cron \
    && crontab /etc/cron.d/cleanup-cron

RUN chmod +x start.sh

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8888/api/v1/health || exit 1

# Expose port
EXPOSE 8888

# Use volumes for persistent data
VOLUME ["/app/downloaded_videos", "/app/logs"]

# Start the app
CMD ["/app/start.sh"]
