"""
Data synchronization service for syncing Toggl data with local database.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date, timedelta
import logging

from app.models.models import Client, Project, Member, TimeEntryCache, SyncLog
from app.models.database import get_db
from toggl_client.enhanced_client import EnhancedTogglClient, TogglAPIError
from config.config import TogglConfig


class SyncService:
    """Service for synchronizing Toggl data with local database."""

    def __init__(self, db: Session, toggl_client: EnhancedTogglClient):
        self.db = db
        self.toggl_client = toggl_client
        self.logger = logging.getLogger(__name__)

    def sync_clients(self, workspace_id: int) -> SyncLog:
        """
        Sync clients from Toggl API to local database.
        
        Args:
            workspace_id: Workspace ID to sync
            
        Returns:
            SyncLog with sync results
        """
        sync_log = SyncLog(
            workspace_id=workspace_id,
            sync_type='clients',
            start_time=datetime.utcnow()
        )
        self.db.add(sync_log)
        self.db.commit()

        try:
            # Fetch clients from Toggl
            toggl_clients = self.toggl_client.get_workspace_clients(workspace_id)
            
            records_processed = len(toggl_clients)
            records_added = 0
            records_updated = 0

            for toggl_client in toggl_clients:
                # Check if client exists
                existing_client = self.db.query(Client).filter(
                    Client.toggl_id == toggl_client.id
                ).first()

                if existing_client:
                    # Update existing client
                    existing_client.name = toggl_client.name
                    existing_client.notes = toggl_client.notes
                    existing_client.external_reference = toggl_client.external_reference
                    existing_client.archived = toggl_client.archived
                    existing_client.workspace_id = toggl_client.workspace_id
                    existing_client.updated_at = datetime.utcnow()
                    records_updated += 1
                else:
                    # Create new client
                    new_client = Client(
                        toggl_id=toggl_client.id,
                        name=toggl_client.name,
                        notes=toggl_client.notes,
                        external_reference=toggl_client.external_reference,
                        archived=toggl_client.archived,
                        workspace_id=toggl_client.workspace_id
                    )
                    self.db.add(new_client)
                    records_added += 1

            self.db.commit()

            # Update sync log
            sync_log.end_time = datetime.utcnow()
            sync_log.status = 'completed'
            sync_log.records_processed = records_processed
            sync_log.records_added = records_added
            sync_log.records_updated = records_updated
            self.db.commit()

            self.logger.info(f"Clients sync completed: {records_added} added, {records_updated} updated")

        except Exception as e:
            sync_log.end_time = datetime.utcnow()
            sync_log.status = 'failed'
            sync_log.error_message = str(e)
            self.db.commit()
            self.logger.error(f"Clients sync failed: {e}")
            raise

        return sync_log

    def sync_projects(self, workspace_id: int) -> SyncLog:
        """
        Sync projects from Toggl API to local database.
        
        Args:
            workspace_id: Workspace ID to sync
            
        Returns:
            SyncLog with sync results
        """
        sync_log = SyncLog(
            workspace_id=workspace_id,
            sync_type='projects',
            start_time=datetime.utcnow()
        )
        self.db.add(sync_log)
        self.db.commit()

        try:
            # Fetch projects from Toggl
            toggl_projects = self.toggl_client.get_workspace_projects(workspace_id)
            
            records_processed = len(toggl_projects)
            records_added = 0
            records_updated = 0

            for toggl_project in toggl_projects:
                # Get local client ID if project has a client
                local_client_id = None
                if toggl_project.client_id:
                    local_client = self.db.query(Client).filter(
                        Client.toggl_id == toggl_project.client_id
                    ).first()
                    if local_client:
                        local_client_id = local_client.id

                # Check if project exists
                existing_project = self.db.query(Project).filter(
                    Project.toggl_id == toggl_project.id
                ).first()

                if existing_project:
                    # Update existing project
                    existing_project.name = toggl_project.name
                    existing_project.client_id = local_client_id
                    existing_project.workspace_id = toggl_project.workspace_id
                    existing_project.billable = toggl_project.billable
                    existing_project.is_private = toggl_project.is_private
                    existing_project.active = toggl_project.active
                    existing_project.color = toggl_project.color
                    existing_project.updated_at = datetime.utcnow()
                    records_updated += 1
                else:
                    # Create new project
                    new_project = Project(
                        toggl_id=toggl_project.id,
                        name=toggl_project.name,
                        client_id=local_client_id,
                        workspace_id=toggl_project.workspace_id,
                        billable=toggl_project.billable,
                        is_private=toggl_project.is_private,
                        active=toggl_project.active,
                        color=toggl_project.color
                    )
                    self.db.add(new_project)
                    records_added += 1

            self.db.commit()

            # Update sync log
            sync_log.end_time = datetime.utcnow()
            sync_log.status = 'completed'
            sync_log.records_processed = records_processed
            sync_log.records_added = records_added
            sync_log.records_updated = records_updated
            self.db.commit()

            self.logger.info(f"Projects sync completed: {records_added} added, {records_updated} updated")

        except Exception as e:
            sync_log.end_time = datetime.utcnow()
            sync_log.status = 'failed'
            sync_log.error_message = str(e)
            self.db.commit()
            self.logger.error(f"Projects sync failed: {e}")
            raise

        return sync_log

    def sync_members(self, workspace_id: int) -> SyncLog:
        """
        Sync workspace members from Toggl API to local database.
        
        Args:
            workspace_id: Workspace ID to sync
            
        Returns:
            SyncLog with sync results
        """
        sync_log = SyncLog(
            workspace_id=workspace_id,
            sync_type='members',
            start_time=datetime.utcnow()
        )
        self.db.add(sync_log)
        self.db.commit()

        try:
            # Fetch members from Toggl
            toggl_users = self.toggl_client.get_workspace_users(workspace_id)
            
            records_processed = len(toggl_users)
            records_added = 0
            records_updated = 0

            for toggl_user in toggl_users:
                # Check if member exists
                existing_member = self.db.query(Member).filter(
                    Member.toggl_id == toggl_user['id']
                ).first()

                if existing_member:
                    # Update existing member
                    existing_member.name = toggl_user.get('name', '')
                    existing_member.email = toggl_user.get('email')
                    existing_member.workspace_id = workspace_id
                    existing_member.active = toggl_user.get('active', True)
                    existing_member.updated_at = datetime.utcnow()
                    records_updated += 1
                else:
                    # Create new member
                    new_member = Member(
                        toggl_id=toggl_user['id'],
                        name=toggl_user.get('name', ''),
                        email=toggl_user.get('email'),
                        workspace_id=workspace_id,
                        active=toggl_user.get('active', True)
                    )
                    self.db.add(new_member)
                    records_added += 1

            self.db.commit()

            # Update sync log
            sync_log.end_time = datetime.utcnow()
            sync_log.status = 'completed'
            sync_log.records_processed = records_processed
            sync_log.records_added = records_added
            sync_log.records_updated = records_updated
            self.db.commit()

            self.logger.info(f"Members sync completed: {records_added} added, {records_updated} updated")

        except Exception as e:
            sync_log.end_time = datetime.utcnow()
            sync_log.status = 'failed'
            sync_log.error_message = str(e)
            self.db.commit()
            self.logger.error(f"Members sync failed: {e}")
            raise

        return sync_log

    def sync_time_entries(self, workspace_id: int, start_date: date, end_date: date) -> SyncLog:
        """
        Sync time entries from Toggl API to local database.
        
        Args:
            workspace_id: Workspace ID to sync
            start_date: Start date for time entries
            end_date: End date for time entries
            
        Returns:
            SyncLog with sync results
        """
        sync_log = SyncLog(
            workspace_id=workspace_id,
            sync_type='time_entries',
            start_time=datetime.utcnow(),
            date_range_start=start_date,
            date_range_end=end_date
        )
        self.db.add(sync_log)
        self.db.commit()

        try:
            # Fetch time entries from Toggl
            time_entries = self.toggl_client.get_workspace_time_entries_with_clients(
                workspace_id,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            records_processed = len(time_entries)
            records_added = 0
            records_updated = 0

            for entry in time_entries:
                # Get local project ID
                local_project_id = None
                if entry.project_id:
                    local_project = self.db.query(Project).filter(
                        Project.toggl_id == entry.project_id
                    ).first()
                    if local_project:
                        local_project_id = local_project.id

                # Parse start and stop times
                start_time = datetime.fromisoformat(entry.start.replace('Z', '+00:00'))
                stop_time = None
                if entry.stop:
                    stop_time = datetime.fromisoformat(entry.stop.replace('Z', '+00:00'))

                # Check if time entry exists
                existing_entry = self.db.query(TimeEntryCache).filter(
                    TimeEntryCache.toggl_id == entry.id
                ).first()

                if existing_entry:
                    # Update existing entry
                    existing_entry.description = entry.description
                    existing_entry.duration = entry.duration
                    existing_entry.start_time = start_time
                    existing_entry.stop_time = stop_time
                    existing_entry.user_id = entry.user_id
                    existing_entry.user_name = entry.user_name
                    existing_entry.project_id = local_project_id
                    existing_entry.project_name = entry.project_name
                    existing_entry.client_id = entry.client_id
                    existing_entry.client_name = entry.client_name
                    existing_entry.workspace_id = entry.workspace_id
                    existing_entry.billable = entry.billable
                    existing_entry.tags = entry.tags
                    existing_entry.updated_at = datetime.utcnow()
                    existing_entry.sync_date = date.today()
                    records_updated += 1
                else:
                    # Create new entry
                    new_entry = TimeEntryCache(
                        toggl_id=entry.id,
                        description=entry.description,
                        duration=entry.duration,
                        start_time=start_time,
                        stop_time=stop_time,
                        user_id=entry.user_id,
                        user_name=entry.user_name,
                        project_id=local_project_id,
                        project_name=entry.project_name,
                        client_id=entry.client_id,
                        client_name=entry.client_name,
                        workspace_id=entry.workspace_id,
                        billable=entry.billable,
                        tags=entry.tags,
                        sync_date=date.today()
                    )
                    self.db.add(new_entry)
                    records_added += 1

            self.db.commit()

            # Update sync log
            sync_log.end_time = datetime.utcnow()
            sync_log.status = 'completed'
            sync_log.records_processed = records_processed
            sync_log.records_added = records_added
            sync_log.records_updated = records_updated
            self.db.commit()

            self.logger.info(f"Time entries sync completed: {records_added} added, {records_updated} updated")

        except Exception as e:
            sync_log.end_time = datetime.utcnow()
            sync_log.status = 'failed'
            sync_log.error_message = str(e)
            self.db.commit()
            self.logger.error(f"Time entries sync failed: {e}")
            raise

        return sync_log

    def full_sync(self, workspace_id: int, time_entries_days: int = 30) -> List[SyncLog]:
        """
        Perform a full sync of all data for a workspace.
        
        Args:
            workspace_id: Workspace ID to sync
            time_entries_days: Number of days back to sync time entries
            
        Returns:
            List of SyncLog objects for each sync operation
        """
        sync_logs = []

        try:
            # 1. Sync clients first (needed for projects)
            self.logger.info(f"Starting full sync for workspace {workspace_id}")
            clients_log = self.sync_clients(workspace_id)
            sync_logs.append(clients_log)

            # 2. Sync projects (needs clients)
            projects_log = self.sync_projects(workspace_id)
            sync_logs.append(projects_log)

            # 3. Sync members
            members_log = self.sync_members(workspace_id)
            sync_logs.append(members_log)

            # 4. Sync time entries for the specified period
            end_date = date.today()
            start_date = end_date - timedelta(days=time_entries_days)
            time_entries_log = self.sync_time_entries(workspace_id, start_date, end_date)
            sync_logs.append(time_entries_log)

            self.logger.info(f"Full sync completed for workspace {workspace_id}")

        except Exception as e:
            self.logger.error(f"Full sync failed for workspace {workspace_id}: {e}")
            raise

        return sync_logs

    def get_sync_status(self, workspace_id: int, limit: int = 10) -> List[SyncLog]:
        """
        Get recent sync logs for a workspace.
        
        Args:
            workspace_id: Workspace ID
            limit: Maximum number of logs to return
            
        Returns:
            List of recent SyncLog objects
        """
        return self.db.query(SyncLog).filter(
            SyncLog.workspace_id == workspace_id
        ).order_by(SyncLog.start_time.desc()).limit(limit).all()

    def cleanup_old_time_entries(self, workspace_id: int, days_to_keep: int = 90) -> int:
        """
        Clean up old time entries from cache.
        
        Args:
            workspace_id: Workspace ID
            days_to_keep: Number of days of data to keep
            
        Returns:
            Number of records deleted
        """
        cutoff_date = date.today() - timedelta(days=days_to_keep)
        
        deleted_count = self.db.query(TimeEntryCache).filter(
            and_(
                TimeEntryCache.workspace_id == workspace_id,
                TimeEntryCache.sync_date < cutoff_date
            )
        ).delete()
        
        self.db.commit()
        
        self.logger.info(f"Cleaned up {deleted_count} old time entries for workspace {workspace_id}")
        return deleted_count


def get_sync_service(db: Session = None, toggl_client: EnhancedTogglClient = None) -> SyncService:
    """
    Factory function to get SyncService instance.
    
    Args:
        db: Database session (if None, will get from dependency)
        toggl_client: Toggl client (if None, will create from config)
        
    Returns:
        SyncService instance
    """
    if db is None:
        db = next(get_db())
    
    if toggl_client is None:
        config = TogglConfig.from_env()
        if config.api_token:
            toggl_client = EnhancedTogglClient(api_token=config.api_token)
        else:
            toggl_client = EnhancedTogglClient(email=config.email, password=config.password)
    
    return SyncService(db, toggl_client)