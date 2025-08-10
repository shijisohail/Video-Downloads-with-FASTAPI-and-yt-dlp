"""
Logging configuration for the application.
"""

import logging
import sys
from pathlib import Path
from app.core.config import settings

def setup_logging():
    """Setup logging configuration."""
    # Create logs directory
    settings.LOGS_DIR.mkdir(exist_ok=True)
    
    # Configure logging formatter
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )

    # File handler for all logs
    file_handler = logging.FileHandler(settings.LOGS_DIR / 'video_downloader.log')
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)

    # File handler for errors only
    error_handler = logging.FileHandler(settings.LOGS_DIR / 'errors.log')
    error_handler.setFormatter(log_formatter)
    error_handler.setLevel(logging.ERROR)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)

    # Setup logger
    logger = logging.getLogger("video_downloader_api")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)

    # Prevent duplicate logs
    logger.propagate = False

    # Log startup
    logger.info(f"=== Video Downloader API v{settings.VERSION} Starting ===")
    logger.info(f"Logs directory: {settings.LOGS_DIR.absolute()}")
    logger.info(f"Downloads directory: {settings.DOWNLOADS_DIR.absolute()}")

    return logger 