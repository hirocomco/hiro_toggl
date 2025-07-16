"""
Background scheduler for automatic sync operations.
"""

import asyncio
import logging
from datetime import datetime, time
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.database import get_db, SessionLocal
from app.services.sync_service import SyncService
from app.services.setting_service import SettingService
from toggl_client import EnhancedTogglClient as TogglClient
from config import TogglConfig


class AutoSyncScheduler:
    """Scheduler for automatic daily sync operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        
    async def start(self):
        """Start the automatic sync scheduler."""
        self.logger.info("Starting automatic sync scheduler")
        self.is_running = True
        
        while self.is_running:
            try:
                await self._run_scheduled_syncs()
                # Wait for 1 hour before checking again
                await asyncio.sleep(3600)  # 1 hour
                
            except Exception as e:
                self.logger.error(f"Error in sync scheduler: {e}")
                # Wait 5 minutes before retrying on error
                await asyncio.sleep(300)
    
    def stop(self):
        """Stop the automatic sync scheduler."""
        self.logger.info("Stopping automatic sync scheduler")
        self.is_running = False
    
    async def _run_scheduled_syncs(self):
        """Run scheduled syncs for all workspaces that need them."""
        db = SessionLocal()
        
        try:
            # Get Toggl client
            config = TogglConfig.from_env()
            if not config.is_valid():
                self.logger.warning("Toggl API credentials not configured, skipping automatic sync")
                return
                
            if config.api_token:
                toggl_client = TogglClient(api_token=config.api_token)
            else:
                toggl_client = TogglClient(email=config.email, password=config.password)
            
            # Create sync service
            sync_service = SyncService(db, toggl_client)
            setting_service = SettingService(db)
            
            # Get all workspaces that have auto_sync enabled
            workspaces_with_auto_sync = self._get_workspaces_with_auto_sync(db, setting_service)
            
            for workspace_id in workspaces_with_auto_sync:
                try:
                    sync_log = sync_service.run_automatic_daily_sync(workspace_id)
                    if sync_log:
                        self.logger.info(f"Automatic sync completed for workspace {workspace_id}")
                    else:
                        self.logger.debug(f"No automatic sync needed for workspace {workspace_id}")
                        
                except Exception as e:
                    self.logger.error(f"Automatic sync failed for workspace {workspace_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error in scheduled sync run: {e}")
            
        finally:
            db.close()
    
    def _get_workspaces_with_auto_sync(self, db: Session, setting_service: SettingService) -> List[int]:
        """Get list of workspace IDs that have auto_sync enabled."""
        # Query settings to find workspaces with auto_sync enabled
        from app.models.models import Setting
        
        auto_sync_settings = db.query(Setting).filter(
            Setting.key == 'auto_sync',
            Setting.value == 'true',
            Setting.workspace_id.isnot(None)
        ).all()
        
        return [setting.workspace_id for setting in auto_sync_settings]


# Background task function for FastAPI
async def run_auto_sync_scheduler():
    """Run the automatic sync scheduler as a background task."""
    scheduler = AutoSyncScheduler()
    await scheduler.start()


# Standalone function for running as a separate process/cron job
def run_single_sync_check():
    """Run a single sync check for all workspaces (for cron job usage)."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    db = SessionLocal()
    
    try:
        # Get Toggl client
        config = TogglConfig.from_env()
        if not config.is_valid():
            logger.warning("Toggl API credentials not configured")
            return
            
        if config.api_token:
            toggl_client = TogglClient(api_token=config.api_token)
        else:
            toggl_client = TogglClient(email=config.email, password=config.password)
        
        # Create services
        sync_service = SyncService(db, toggl_client)
        setting_service = SettingService(db)
        
        # Get workspaces with auto_sync enabled
        from app.models.models import Setting
        
        auto_sync_settings = db.query(Setting).filter(
            Setting.key == 'auto_sync',
            Setting.value == 'true',
            Setting.workspace_id.isnot(None)
        ).all()
        
        for setting in auto_sync_settings:
            workspace_id = setting.workspace_id
            try:
                sync_log = sync_service.run_automatic_daily_sync(workspace_id)
                if sync_log:
                    logger.info(f"Automatic sync completed for workspace {workspace_id}")
                else:
                    logger.debug(f"No automatic sync needed for workspace {workspace_id}")
                    
            except Exception as e:
                logger.error(f"Automatic sync failed for workspace {workspace_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in single sync check: {e}")
        
    finally:
        db.close()


if __name__ == "__main__":
    # Run as standalone script
    run_single_sync_check() 