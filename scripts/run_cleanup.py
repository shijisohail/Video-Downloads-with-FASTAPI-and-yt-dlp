#!/usr/bin/env python3
"""
Standalone cleanup script for cron jobs.
"""

import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.cleanup import CleanupService
from config.logging import setup_logging

async def main():
    """Run cleanup process."""
    # Setup logging
    logger = setup_logging()
    
    try:
        logger.info("Starting standalone cleanup process...")
        
        cleanup_service = CleanupService()
        await cleanup_service.cleanup_old_files()
        await cleanup_service.cleanup_expired_statuses()
        
        logger.info("Standalone cleanup process completed successfully")
        
    except Exception as e:
        logger.error(f"Standalone cleanup process failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
