FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=UTC

# Install dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    gnupg \
    curl \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for cookie extraction (optional)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Copy files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Copy cookie files (if they exist)
COPY cookies/ ./cookies/

# Create required directories
RUN mkdir -p downloads logs static cookies \
    && chmod 755 downloads logs static cookies

# Make scripts executable
RUN chmod +x scripts/*.py

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app

# Setup cron job for cleanup (every 30 mins)
RUN echo "*/30 * * * * cd /app && /usr/local/bin/python3 scripts/run_cleanup.py >> /app/logs/cron.log 2>&1" > /etc/cron.d/cleanup-cron \
    && chmod 0644 /etc/cron.d/cleanup-cron \
    && crontab /etc/cron.d/cleanup-cron

# Copy start script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8888/api/v1/health || exit 1

# Expose port
EXPOSE 8888

# Use volumes for persistent data
VOLUME ["/app/downloads", "/app/logs"]

# Start the app (cron as root, FastAPI as appuser)
CMD ["/app/start.sh"]
