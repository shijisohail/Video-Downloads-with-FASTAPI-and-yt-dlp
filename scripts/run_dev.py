#!/usr/bin/env python3
"""
Development server runner script.
"""

import uvicorn
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from config.logging import setup_logging

def main():
    """Run the development server."""
    # Setup logging
    logger = setup_logging()
    
    # Ensure directories exist
    settings.DOWNLOADS_DIR.mkdir(exist_ok=True)
    settings.LOGS_DIR.mkdir(exist_ok=True)
    settings.STATIC_DIR.mkdir(exist_ok=True)
    
    logger.info("Starting development server...")
    logger.info(f"Server will be available at: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"API documentation at: http://{settings.HOST}:{settings.PORT}/docs")
    
    # Run the server
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
