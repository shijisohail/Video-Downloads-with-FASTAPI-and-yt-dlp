"""
Scheduler management for background tasks.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.cleanup import CleanupService

logger = logging.getLogger(__name__)

class SchedulerManager:
    """Scheduler manager for background tasks."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.cleanup_service = CleanupService()
    
    async def start(self) -> None:
        """Start the scheduler."""
        try:
            self.scheduler.start()
            logger.info("Scheduler started successfully")
            
            # Add cleanup jobs
            self._add_cleanup_jobs()
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the scheduler."""
        try:
            self.scheduler.shutdown()
            logger.info("Scheduler shut down successfully")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {str(e)}")
    
    def _add_cleanup_jobs(self) -> None:
        """Add cleanup jobs to scheduler."""
        # Hourly cleanup
        self.scheduler.add_job(
            self.cleanup_service.cleanup_old_files,
            CronTrigger(minute=0),  # Run at the top of every hour
            id='cleanup_old_files',
            name='Cleanup old video files',
            replace_existing=True
        )
        logger.info("Cleanup job scheduled to run every hour")
        
        # Frequent cleanup (every 30 minutes)
        self.scheduler.add_job(
            self.cleanup_service.cleanup_old_files,
            CronTrigger(minute="0,30"),  # Run at 0 and 30 minutes of every hour
            id='frequent_cleanup',
            name='Frequent cleanup of old video files',
            replace_existing=True
        )
        logger.info("Frequent cleanup job scheduled to run every 30 minutes")
    
    def add_job(self, func, trigger, **kwargs) -> None:
        """Add a job to the scheduler."""
        self.scheduler.add_job(func, trigger, **kwargs)
    
    def remove_job(self, job_id: str) -> None:
        """Remove a job from the scheduler."""
        self.scheduler.remove_job(job_id)
    
    def get_jobs(self) -> list:
        """Get all scheduled jobs."""
        return self.scheduler.get_jobs()

# Global scheduler instance
scheduler = SchedulerManager() 