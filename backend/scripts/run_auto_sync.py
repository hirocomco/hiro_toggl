#!/usr/bin/env python3
"""
Standalone script to run automatic daily sync.
Can be run as a cron job or scheduled task.

Usage:
    python run_auto_sync.py

Cron job example (run every hour):
    0 * * * * /usr/bin/python3 /path/to/run_auto_sync.py

Environment variables required:
    - TOGGL_API_TOKEN or TOGGL_EMAIL/TOGGL_PASSWORD
    - DATABASE_URL
"""

import os
import sys
import logging
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.scheduler import run_single_sync_check


def setup_logging():
    """Setup logging configuration."""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            # Optional: Add file handler
            # logging.FileHandler('/var/log/toggl-auto-sync.log')
        ]
    )


def main():
    """Main entry point for the auto sync script."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting automatic sync check")
    
    try:
        # Check required environment variables
        required_env_vars = ['DATABASE_URL']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            return 1
        
        # Check Toggl credentials
        if not os.getenv('TOGGL_API_TOKEN') and not (os.getenv('TOGGL_EMAIL') and os.getenv('TOGGL_PASSWORD')):
            logger.error("Missing Toggl API credentials. Set TOGGL_API_TOKEN or TOGGL_EMAIL/TOGGL_PASSWORD")
            return 1
        
        # Run the sync check
        run_single_sync_check()
        
        logger.info("Automatic sync check completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error in automatic sync check: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main()) 