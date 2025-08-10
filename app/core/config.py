"""
Application configuration settings.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    # Application info
    VERSION: str = "2.1.0"
    APP_NAME: str = "Video Downloader API"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8888
    DEBUG: bool = False
    
    # File paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DOWNLOADS_DIR: Path = BASE_DIR / "downloads"
    LOGS_DIR: Path = BASE_DIR / "logs"
    STATIC_DIR: Path = BASE_DIR / "static"
    
    # Cleanup settings
    CLEANUP_INTERVAL_HOURS: int = 5
    CLEANUP_FREQUENCY_MINUTES: int = 30
    
    # Download settings
    MAX_RETRIES: int = 10
    SOCKET_TIMEOUT: int = 60
    CHUNK_SIZE: int = 10485760  # 10MB
    
    # Cookie settings
    COOKIE_DIR: Path = BASE_DIR / "cookies"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()

# Ensure directories exist
settings.DOWNLOADS_DIR.mkdir(exist_ok=True)
settings.LOGS_DIR.mkdir(exist_ok=True)
settings.STATIC_DIR.mkdir(exist_ok=True)
settings.COOKIE_DIR.mkdir(exist_ok=True) 