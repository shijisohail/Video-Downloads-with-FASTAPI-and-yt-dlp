"""
Cleanup service for file management.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import settings
from app.core.storage import download_storage, file_manager

logger = logging.getLogger(__name__)

class CleanupService:
    """Service for cleaning up old files and statuses."""
    
    def __init__(self):
        self.downloads_dir = settings.DOWNLOADS_DIR
    
    async def cleanup_old_files(self):
        """Delete video files older than configured hours."""
        try:
            logger.info("Starting cleanup of old video files...")
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=settings.CLEANUP_INTERVAL_HOURS)
            deleted_count = 0
            total_size_freed = 0

            # Get all files in downloads directory
            for file_path in self.downloads_dir.iterdir():
                if file_path.is_file():
                    try:
                        # Check file modification time
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                        if file_mtime < cutoff_time:
                            # Get file size before deletion
                            file_size = file_path.stat().st_size

                            # Delete the file
                            file_path.unlink()
                            deleted_count += 1
                            total_size_freed += file_size

                            logger.info(f"Deleted old file: {file_path.name} (created: {file_mtime})")

                            # Also clean up from download_status if it exists
                            self._cleanup_download_status(file_path.name)

                    except Exception as file_error:
                        logger.error(f"Error processing file {file_path.name}: {file_error}")

            if deleted_count > 0:
                size_mb = total_size_freed / (1024 * 1024)
                logger.info(f"Cleanup completed: {deleted_count} files deleted, {size_mb:.2f} MB freed")
            else:
                logger.info("Cleanup completed: No old files found")

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            raise

    def _cleanup_download_status(self, filename: str):
        """Clean up download status for deleted files."""
        # Extract task_id from filename if possible
        if '_' in filename:
            potential_task_id = filename.split('_')[0]
            status_data = download_storage.get_status(potential_task_id)
            
            if status_data:
                # Update status to indicate file was cleaned up
                download_storage.update_status(potential_task_id, {
                    'status': 'cleaned_up',
                    'message': f'File automatically deleted after {settings.CLEANUP_INTERVAL_HOURS} hours',
                    'download_url': None
                })
                logger.debug(f"Updated status for cleaned up task: {potential_task_id}")

    async def cleanup_expired_statuses(self):
        """Clean up expired download statuses."""
        try:
            expired_count = download_storage.cleanup_expired()
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired download statuses")
        except Exception as e:
            logger.error(f"Error cleaning up expired statuses: {str(e)}")

    async def get_cleanup_stats(self):
        """Get cleanup statistics."""
        try:
            current_files = len(file_manager.list_downloads())
            total_statuses = len(download_storage.get_all_statuses())
            
            return {
                "current_files": current_files,
                "total_statuses": total_statuses,
                "cleanup_interval_hours": settings.CLEANUP_INTERVAL_HOURS,
                "cleanup_frequency_minutes": settings.CLEANUP_FREQUENCY_MINUTES
            }
        except Exception as e:
            logger.error(f"Error getting cleanup stats: {str(e)}")
            return {} 