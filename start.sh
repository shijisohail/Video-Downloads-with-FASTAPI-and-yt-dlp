#!/bin/bash

echo "▶️ Starting cron as root"
/usr/sbin/cron

echo "🚀 Starting FastAPI as appuser"
exec su appuser -c "python scripts/run_prod.py"
