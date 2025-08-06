#!/bin/bash

echo "▶️ Starting cron as root"
/usr/sbin/cron

echo "🚀 Starting FastAPI as appuser"
exec su appuser -c "uvicorn main:app --host 0.0.0.0 --port 8888"
