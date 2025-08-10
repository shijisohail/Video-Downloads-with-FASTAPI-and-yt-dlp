"""
Logs-related API endpoints.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/logs")
async def get_logs_info():
    """Get information about available log files."""
    try:
        log_files = []
        if settings.LOGS_DIR.exists():
            for log_file in settings.LOGS_DIR.glob("*.log"):
                stat = log_file.stat()
                log_files.append({
                    "filename": log_file.name,
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "url": f"/api/v1/logs/{log_file.name}"
                })

        return {
            "logs_directory": str(settings.LOGS_DIR),
            "available_logs": log_files,
            "total_files": len(log_files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error accessing logs: {str(e)}")

@router.get("/logs/{filename}")
async def get_log_file(filename: str, lines: int = 100):
    """Get log file contents (last N lines)."""
    try:
        log_file_path = settings.LOGS_DIR / filename

        # Security check - only allow .log files
        if not filename.endswith(".log"):
            raise HTTPException(status_code=400, detail="Only .log files are allowed")

        if not log_file_path.exists():
            raise HTTPException(status_code=404, detail="Log file not found")

        # Read the last N lines
        with open(log_file_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        return {
            "filename": filename,
            "total_lines": len(all_lines),
            "returned_lines": len(last_lines),
            "requested_lines": lines,
            "content": ''.join(last_lines)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading log file: {str(e)}") 