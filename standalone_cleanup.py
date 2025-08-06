#!/usr/bin/env python3
"""
Standalone cleanup script for video downloader
This can be run independently or via cron job
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
import traceback

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.absolute()

# Setup paths
DOWNLOADS_DIR = SCRIPT_DIR / "downloads"
LOGS_DIR = SCRIPT_DIR / "logs"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Setup logging for the cleanup script
cleanup_logger = logging.getLogger("cleanup_script")
cleanup_logger.setLevel(logging.INFO)

# Create file handler for cleanup logs
cleanup_log_file = LOGS_DIR / 'cleanup.log'
file_handler = logging.FileHandler(cleanup_log_file)
file_handler.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
cleanup_logger.addHandler(file_handler)
cleanup_logger.addHandler(console_handler)


def cleanup_old_files(max_age_hours=5):
    """
    Delete video files older than specified hours

    Args:
        max_age_hours (int): Maximum age in hours before files are deleted
    """
    try:
        cleanup_logger.info(f"Starting cleanup of files older than {max_age_hours} hours...")

        if not DOWNLOADS_DIR.exists():
            cleanup_logger.warning(f"Downloads directory does not exist: {DOWNLOADS_DIR}")
            return

        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=max_age_hours)

        deleted_count = 0
        total_size_freed = 0
        skipped_count = 0
        error_count = 0

        # Get all files in downloads directory
        files_to_process = [f for f in DOWNLOADS_DIR.iterdir() if f.is_file()]
        cleanup_logger.info(f"Found {len(files_to_process)} files to process")

        for file_path in files_to_process:
            try:
                # Check file modification time
                file_stat = file_path.stat()
                file_mtime = datetime.fromtimestamp(file_stat.st_mtime)

                if file_mtime < cutoff_time:
                    # Get file size before deletion
                    file_size = file_stat.st_size

                    # Delete the file
                    file_path.unlink()
                    deleted_count += 1
                    total_size_freed += file_size

                    cleanup_logger.info(
                        f"Deleted: {file_path.name} (created: {file_mtime.strftime('%Y-%m-%d %H:%M:%S')}, size: {file_size} bytes)")
                else:
                    skipped_count += 1
                    cleanup_logger.debug(
                        f"Skipped: {file_path.name} (too recent: {file_mtime.strftime('%Y-%m-%d %H:%M:%S')})")

            except Exception as file_error:
                error_count += 1
                cleanup_logger.error(f"Error processing file {file_path.name}: {file_error}")

        # Log summary
        size_mb = total_size_freed / (1024 * 1024)
        cleanup_logger.info(f"Cleanup completed:")
        cleanup_logger.info(f"  - Files deleted: {deleted_count}")
        cleanup_logger.info(f"  - Files skipped (too recent): {skipped_count}")
        cleanup_logger.info(f"  - Files with errors: {error_count}")
        cleanup_logger.info(f"  - Space freed: {size_mb:.2f} MB")

        return {
            "deleted_count": deleted_count,
            "skipped_count": skipped_count,
            "error_count": error_count,
            "total_size_freed": total_size_freed
        }

    except Exception as e:
        cleanup_logger.error(f"Critical error during cleanup: {str(e)}")
        cleanup_logger.error(f"Cleanup traceback: {traceback.format_exc()}")
        return None


def cleanup_old_logs(max_age_days=30):
    """
    Clean up old log files to prevent disk space issues

    Args:
        max_age_days (int): Maximum age in days before log files are deleted
    """
    try:
        cleanup_logger.info(f"Starting cleanup of log files older than {max_age_days} days...")

        if not LOGS_DIR.exists():
            cleanup_logger.warning(f"Logs directory does not exist: {LOGS_DIR}")
            return

        current_time = datetime.now()
        cutoff_time = current_time - timedelta(days=max_age_days)

        deleted_count = 0
        total_size_freed = 0

        # Get all log files (but preserve current cleanup log and recent main logs)
        log_files = [f for f in LOGS_DIR.glob("*.log") if f.is_file()]
        current_cleanup_log = cleanup_log_file.name

        for log_file in log_files:
            # Don't delete the current cleanup log or very recent logs
            if log_file.name == current_cleanup_log:
                continue

            try:
                file_stat = log_file.stat()
                file_mtime = datetime.fromtimestamp(file_stat.st_mtime)

                if file_mtime < cutoff_time:
                    file_size = file_stat.st_size
                    log_file.unlink()
                    deleted_count += 1
                    total_size_freed += file_size
                    cleanup_logger.info(
                        f"Deleted old log: {log_file.name} (modified: {file_mtime.strftime('%Y-%m-%d %H:%M:%S')})")

            except Exception as file_error:
                cleanup_logger.error(f"Error processing log file {log_file.name}: {file_error}")

        if deleted_count > 0:
            size_mb = total_size_freed / (1024 * 1024)
            cleanup_logger.info(f"Log cleanup completed: {deleted_count} files deleted, {size_mb:.2f} MB freed")
        else:
            cleanup_logger.info("Log cleanup completed: No old log files found")

    except Exception as e:
        cleanup_logger.error(f"Error during log cleanup: {str(e)}")


def main():
    """Main cleanup function"""
    cleanup_logger.info("=" * 60)
    cleanup_logger.info("Video Downloader Cleanup Script Started")
    cleanup_logger.info("=" * 60)

    # Cleanup video files older than 5 hours
    video_cleanup_result = cleanup_old_files(max_age_hours=5)

    # Cleanup log files older than 30 days
    cleanup_old_logs(max_age_days=30)

    cleanup_logger.info("=" * 60)
    cleanup_logger.info("Cleanup Script Completed")
    cleanup_logger.info("=" * 60)

    # Return exit code based on success
    if video_cleanup_result is not None:
        return 0  # Success
    else:
        return 1  # Error occurred


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)