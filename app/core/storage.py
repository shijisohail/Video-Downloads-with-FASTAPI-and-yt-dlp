"""
Storage management for download status and file operations.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

class DownloadStorage:
    """In-memory storage for download status."""
    
    def __init__(self):
        self._storage: Dict[str, Dict[str, Any]] = {}
    
    def set_status(self, task_id: str, status_data: Dict[str, Any]) -> None:
        """Set download status for a task."""
        self._storage[task_id] = status_data
        logger.debug(f"Status set for task {task_id}: {status_data.get('status')}")
    
    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get download status for a task."""
        return self._storage.get(task_id)
    
    def update_status(self, task_id: str, updates: Dict[str, Any]) -> None:
        """Update download status for a task."""
        if task_id in self._storage:
            self._storage[task_id].update(updates)
            logger.debug(f"Status updated for task {task_id}")
    
    def delete_status(self, task_id: str) -> None:
        """Delete download status for a task."""
        if task_id in self._storage:
            del self._storage[task_id]
            logger.debug(f"Status deleted for task {task_id}")
    
    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get all download statuses."""
        return self._storage.copy()
    
    def cleanup_expired(self) -> int:
        """Clean up expired download statuses."""
        current_time = datetime.now()
        expired_tasks = []
        
        for task_id, status_data in self._storage.items():
            expires_at = status_data.get('expires_at')
            if expires_at:
                try:
                    expiration_time = datetime.fromisoformat(expires_at)
                    if current_time > expiration_time:
                        expired_tasks.append(task_id)
                except ValueError:
                    logger.warning(f"Invalid expiration time for task {task_id}")
        
        for task_id in expired_tasks:
            self.delete_status(task_id)
        
        if expired_tasks:
            logger.info(f"Cleaned up {len(expired_tasks)} expired download statuses")
        
        return len(expired_tasks)

# Global storage instance
download_storage = DownloadStorage()

class FileManager:
    """File system operations manager."""
    
    @staticmethod
    def ensure_directories() -> None:
        """Ensure all required directories exist."""
        settings.DOWNLOADS_DIR.mkdir(exist_ok=True)
        settings.LOGS_DIR.mkdir(exist_ok=True)
        settings.STATIC_DIR.mkdir(exist_ok=True)
        logger.info("All required directories ensured")
    
    @staticmethod
    def get_download_path(filename: str) -> Path:
        """Get full path for a download file."""
        return settings.DOWNLOADS_DIR / filename
    
    @staticmethod
    def file_exists(filename: str) -> bool:
        """Check if a file exists in downloads directory."""
        return settings.DOWNLOADS_DIR.joinpath(filename).exists()
    
    @staticmethod
    def list_downloads() -> list:
        """List all files in downloads directory."""
        return [f.name for f in settings.DOWNLOADS_DIR.iterdir() if f.is_file()]
    
    @staticmethod
    def get_file_size(filename: str) -> Optional[int]:
        """Get file size in bytes."""
        file_path = settings.DOWNLOADS_DIR / filename
        if file_path.exists():
            return file_path.stat().st_size
        return None

# Global file manager instance
file_manager = FileManager() 