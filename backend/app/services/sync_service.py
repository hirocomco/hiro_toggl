"""
Data synchronization service for syncing Toggl data with local database.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date, timedelta
import logging
from fastapi import Depends

from app.models.models import Client, Project, Member, TimeEntryCache, SyncLog
from app.models.database import get_db
from toggl_client import EnhancedTogglClient as TogglClient, TogglAPIError
from config import TogglConfig


class SyncService:
    """Service for synchronizing Toggl data with local database."""

    def __init__(self, db: Session, toggl_client: TogglClient):
        self.db = db
        self.toggl_client = toggl_client
        self.logger = logging.getLogger(__name__)

    def _validate_rate_limits(self, sync_type: str, time_entries_days: int = 0) -> None:
        """
        Validate that the sync won't exceed Toggl API rate limits.
        
        Free plan: 30 requests/hour
        Premium plan: 600 requests/hour
        
        Args:
            sync_type: Type of sync being performed
            time_entries_days: Number of days for time entries (if applicable)
        """
        # Estimate API calls needed
        base_calls = {
            'clients': 1,
            'projects': 1, 
            'members': 1,
            'time_entries': 3,  # projects + clients + time_entries
            'full': 6,  # clients + projects + members + time_entries calls
            'metadata': 3,  # clients + projects + members
            'time_entries_only': 3  # projects + clients + time_entries
        }
        
        estimated_calls = base_calls.get(sync_type, 1)
        
        # For time entries, estimate pagination calls based on data volume
        if sync_type in ['time_entries', 'time_entries_only', 'full'] and time_entries_days > 0:
            # Pagination: 50 entries per API call, estimate based on typical usage
            # Conservative estimate: 2-5 entries per day for active workspace
            estimated_entries = time_entries_days * 3  # 3 entries per day average
            pagination_calls = max(1, (estimated_entries + 49) // 50)  # Round up
            
            # Cap at reasonable maximum to prevent overestimation
            pagination_calls = min(pagination_calls, 50)  # Max 50 pages for estimation
            
            estimated_calls += pagination_calls
        
        # Check against free plan limits (30 requests/hour)
        if estimated_calls > 25:  # Leave some buffer
            raise Exception(
                f"Sync would require ~{estimated_calls} API calls, exceeding free plan limit of 30/hour. "
                f"Try reducing time range to {min(30, time_entries_days // 2)} days or upgrade to Premium plan."
            )
        
        # Log warning for high usage
        if estimated_calls > 15:
            self.logger.warning(
                f"Sync will use ~{estimated_calls} API calls. Free plan limit is 30/hour. "
                f"Consider smaller time ranges or Premium plan for better performance."
            )

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
        # Calculate days for rate limit validation
        time_entries_days = (end_date - start_date).days
        self._validate_rate_limits('time_entries', time_entries_days)
        
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
        # Validate rate limits before starting
        self._validate_rate_limits('full', time_entries_days)
        
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

    def sync_metadata(self, workspace_id: int) -> List[SyncLog]:
        """
        Sync only metadata (clients, projects, members) for a workspace.
        
        This is a lightweight sync that updates relatively static data
        without syncing time entries. Useful for staying under API rate limits.
        
        Args:
            workspace_id: Workspace ID to sync
            
        Returns:
            List of SyncLog objects for metadata sync operations
        """
        # Validate rate limits before starting
        self._validate_rate_limits('metadata')
        
        sync_logs = []

        try:
            self.logger.info(f"Starting metadata sync for workspace {workspace_id}")
            
            # 1. Sync clients first (needed for projects)
            clients_log = self.sync_clients(workspace_id)
            sync_logs.append(clients_log)

            # 2. Sync projects (needs clients)
            projects_log = self.sync_projects(workspace_id)
            sync_logs.append(projects_log)

            # 3. Sync members
            members_log = self.sync_members(workspace_id)
            sync_logs.append(members_log)

            self.logger.info(f"Metadata sync completed for workspace {workspace_id}")

        except Exception as e:
            self.logger.error(f"Metadata sync failed for workspace {workspace_id}: {e}")
            raise

        return sync_logs

    def sync_time_entries_only(self, workspace_id: int, time_entries_days: int = 7) -> SyncLog:
        """
        Sync only time entries for a workspace.
        
        This is a lightweight sync that updates frequently changing time entry data
        without syncing metadata. Useful for frequent updates while staying under API rate limits.
        
        Args:
            workspace_id: Workspace ID to sync
            time_entries_days: Number of days back to sync time entries (default: 7 for recent data)
            
        Returns:
            SyncLog object for time entries sync operation
        """
        try:
            self.logger.info(f"Starting time entries sync for workspace {workspace_id}")
            
            # Sync time entries for the specified period
            end_date = date.today()
            start_date = end_date - timedelta(days=time_entries_days)
            time_entries_log = self.sync_time_entries(workspace_id, start_date, end_date)

            self.logger.info(f"Time entries sync completed for workspace {workspace_id}")
            return time_entries_log

        except Exception as e:
            self.logger.error(f"Time entries sync failed for workspace {workspace_id}: {e}")
            raise

    def chunked_historical_sync(self, workspace_id: int, total_days: int = 365, 
                               chunk_size: int = 30) -> List[SyncLog]:
        """
        Perform a chunked historical sync to get all historical data while staying within API limits.
        
        This method breaks up a large historical sync into smaller chunks that can be run
        over multiple hours to stay within the free plan's 30 API calls/hour limit.
        
        Args:
            workspace_id: Workspace ID to sync
            total_days: Total number of days to sync back
            chunk_size: Size of each chunk in days (default: 30 for free plan)
            
        Returns:
            List of SyncLog objects for each chunk operation
        """
        # First, ensure metadata is synced
        self.logger.info(f"Starting chunked historical sync for workspace {workspace_id}")
        self.logger.info(f"Total days: {total_days}, chunk size: {chunk_size}")
        
        # Step 1: Sync metadata first (only needs to be done once)
        metadata_logs = self.sync_metadata(workspace_id)
        
        # Step 2: Calculate chunks
        end_date = date.today()
        all_sync_logs = metadata_logs.copy()
        
        # Process chunks from most recent to oldest
        for chunk_start in range(0, total_days, chunk_size):
            chunk_end = min(chunk_start + chunk_size - 1, total_days - 1)
            
            # Calculate actual dates for this chunk
            chunk_start_date = end_date - timedelta(days=chunk_end)
            chunk_end_date = end_date - timedelta(days=chunk_start)
            
            self.logger.info(f"Processing chunk: {chunk_start_date} to {chunk_end_date}")
            
            try:
                # Validate this chunk won't exceed rate limits
                chunk_days = (chunk_end_date - chunk_start_date).days + 1
                self._validate_rate_limits('time_entries', chunk_days)
                
                # Sync time entries for this chunk
                chunk_log = self.sync_time_entries(workspace_id, chunk_start_date, chunk_end_date)
                all_sync_logs.append(chunk_log)
                
                self.logger.info(f"Chunk completed: {chunk_log.records_added} added, {chunk_log.records_updated} updated")
                
            except Exception as e:
                self.logger.error(f"Chunk failed ({chunk_start_date} to {chunk_end_date}): {e}")
                
                # Create a failed sync log for this chunk
                failed_log = SyncLog(
                    workspace_id=workspace_id,
                    sync_type='time_entries',
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    status='failed',
                    error_message=str(e),
                    date_range_start=chunk_start_date,
                    date_range_end=chunk_end_date
                )
                self.db.add(failed_log)
                self.db.commit()
                all_sync_logs.append(failed_log)
                
                # Continue with next chunk instead of failing entirely
                continue
        
        self.logger.info(f"Chunked historical sync completed for workspace {workspace_id}")
        return all_sync_logs

    def safe_chunked_historical_sync(self, workspace_id: int, total_days: int = 365, 
                                   chunk_size: int = 30, chunks_per_call: int = 1) -> dict:
        """
        Perform a rate-limit-safe chunked historical sync that processes only a limited number of chunks per call.
        
        This method is designed to be called multiple times to gradually sync historical data
        while staying within the free plan's 30 API calls/hour limit.
        
        Args:
            workspace_id: Workspace ID to sync
            total_days: Total number of days to sync back
            chunk_size: Size of each chunk in days (default: 30 for free plan)
            chunks_per_call: Number of chunks to process in this call (default: 1)
            
        Returns:
            Dictionary with sync progress and results
        """
        self.logger.info(f"Starting safe chunked historical sync for workspace {workspace_id}")
        self.logger.info(f"Total days: {total_days}, chunk size: {chunk_size}, chunks per call: {chunks_per_call}")
        
        # Get the next chunk(s) to process
        next_chunks = self.get_next_historical_chunks(workspace_id, total_days, chunk_size, chunks_per_call)
        
        if not next_chunks['chunks_to_process']:
            return {
                'status': 'completed',
                'message': 'All chunks have been processed',
                'chunks_processed': 0,
                'chunks_remaining': 0,
                'total_chunks': next_chunks['total_chunks'],
                'sync_logs': []
            }
        
        # First sync metadata if this is the first chunk
        sync_logs = []
        if next_chunks['is_first_chunk']:
            try:
                metadata_logs = self.sync_metadata(workspace_id)
                sync_logs.extend(metadata_logs)
                self.logger.info("Metadata sync completed")
            except Exception as e:
                self.logger.error(f"Metadata sync failed: {e}")
                return {
                    'status': 'failed',
                    'message': f'Metadata sync failed: {e}',
                    'chunks_processed': 0,
                    'chunks_remaining': len(next_chunks['chunks_to_process']),
                    'total_chunks': next_chunks['total_chunks'],
                    'sync_logs': []
                }
        
        # Process the chunks
        chunks_processed = 0
        for chunk_info in next_chunks['chunks_to_process']:
            chunk_start_date = chunk_info['start_date']
            chunk_end_date = chunk_info['end_date']
            
            self.logger.info(f"Processing chunk: {chunk_start_date} to {chunk_end_date}")
            
            try:
                # Validate this chunk won't exceed rate limits
                chunk_days = (chunk_end_date - chunk_start_date).days + 1
                self._validate_rate_limits('time_entries', chunk_days)
                
                # Sync time entries for this chunk
                chunk_log = self.sync_time_entries(workspace_id, chunk_start_date, chunk_end_date)
                sync_logs.append(chunk_log)
                chunks_processed += 1
                
                self.logger.info(f"Chunk completed: {chunk_log.records_added} added, {chunk_log.records_updated} updated")
                
            except Exception as e:
                self.logger.error(f"Chunk failed ({chunk_start_date} to {chunk_end_date}): {e}")
                
                # Create a failed sync log for this chunk
                failed_log = SyncLog(
                    workspace_id=workspace_id,
                    sync_type='time_entries',
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    status='failed',
                    error_message=str(e),
                    date_range_start=chunk_start_date,
                    date_range_end=chunk_end_date
                )
                self.db.add(failed_log)
                self.db.commit()
                sync_logs.append(failed_log)
                
                # Stop processing if we hit an error
                break
        
        # Calculate remaining chunks
        remaining_chunks = max(0, next_chunks['total_chunks'] - next_chunks['chunks_completed'] - chunks_processed)
        
        result = {
            'status': 'in_progress' if remaining_chunks > 0 else 'completed',
            'message': f'Processed {chunks_processed} chunk(s). {remaining_chunks} remaining.',
            'chunks_processed': chunks_processed,
            'chunks_remaining': remaining_chunks,
            'total_chunks': next_chunks['total_chunks'],
            'sync_logs': sync_logs
        }
        
        self.logger.info(f"Safe chunked sync result: {result['message']}")
        return result

    def get_next_historical_chunks(self, workspace_id: int, total_days: int = 365, 
                                 chunk_size: int = 30, chunks_to_get: int = 1) -> dict:
        """
        Get the next chunk(s) to process for historical sync.
        
        This method analyzes completed sync logs to determine which chunks still need processing.
        
        Args:
            workspace_id: Workspace ID to sync
            total_days: Total number of days to sync back
            chunk_size: Size of each chunk in days
            chunks_to_get: Number of chunks to return
            
        Returns:
            Dictionary with chunk information and progress
        """
        end_date = date.today()
        total_chunks = (total_days + chunk_size - 1) // chunk_size
        
        # Find completed chunks by looking at sync logs
        completed_chunks = set()
        sync_logs = self.db.query(SyncLog).filter(
            SyncLog.workspace_id == workspace_id,
            SyncLog.sync_type == 'time_entries',
            SyncLog.status == 'completed',
            SyncLog.date_range_start.isnot(None),
            SyncLog.date_range_end.isnot(None)
        ).all()
        
        for log in sync_logs:
            if log.date_range_start and log.date_range_end:
                # Calculate which chunk this log covers
                days_from_today = (end_date - log.date_range_end).days
                chunk_index = days_from_today // chunk_size
                if chunk_index >= 0 and chunk_index < total_chunks:
                    completed_chunks.add(chunk_index)
        
        # Find next chunks to process
        chunks_to_process = []
        for chunk_index in range(total_chunks):
            if chunk_index not in completed_chunks:
                chunk_start_pos = chunk_index * chunk_size
                chunk_end_pos = min(chunk_start_pos + chunk_size - 1, total_days - 1)
                
                chunk_start_date = end_date - timedelta(days=chunk_end_pos)
                chunk_end_date = end_date - timedelta(days=chunk_start_pos)
                
                chunks_to_process.append({
                    'chunk_index': chunk_index,
                    'start_date': chunk_start_date,
                    'end_date': chunk_end_date,
                    'days': (chunk_end_date - chunk_start_date).days + 1
                })
                
                if len(chunks_to_process) >= chunks_to_get:
                    break
        
        return {
            'chunks_to_process': chunks_to_process,
            'chunks_completed': len(completed_chunks),
            'total_chunks': total_chunks,
            'is_first_chunk': len(completed_chunks) == 0,
            'progress_percentage': (len(completed_chunks) / total_chunks) * 100 if total_chunks > 0 else 0
        }

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

    def get_daily_sync_recommendation(self, workspace_id: int) -> Dict[str, Any]:
        """
        Get recommendation for daily sync based on recent activity and API limits.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            Dictionary with sync recommendations
        """
        # Check last successful sync
        last_sync = self.db.query(SyncLog).filter(
            SyncLog.workspace_id == workspace_id,
            SyncLog.sync_type == 'time_entries',
            SyncLog.status == 'completed'
        ).order_by(SyncLog.end_time.desc()).first()
        
        today = date.today()
        
        if last_sync and last_sync.date_range_end:
            # Calculate gap since last sync
            days_since_sync = (today - last_sync.date_range_end).days
            recommended_days = max(1, days_since_sync + 1)  # +1 to ensure overlap
        else:
            # No previous sync, recommend starting small
            recommended_days = 7
        
        # Cap at 30 days for free plan safety
        recommended_days = min(recommended_days, 30)
        
        # Estimate API calls for this sync
        estimated_calls = 3  # Base calls for time entries
        estimated_entries = recommended_days * 3  # Conservative estimate
        pagination_calls = max(1, (estimated_entries + 49) // 50)
        estimated_calls += pagination_calls
        
        return {
            'recommended_days': recommended_days,
            'estimated_api_calls': estimated_calls,
            'is_safe_for_free_plan': estimated_calls <= 25,
            'last_sync_date': last_sync.date_range_end if last_sync else None,
            'sync_type': 'time_entries_only'
        }

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

    def should_run_automatic_sync(self, workspace_id: int) -> bool:
        """
        Check if automatic sync should run based on settings and last sync time.
        
        Args:
            workspace_id: Workspace ID to check
            
        Returns:
            Boolean indicating if automatic sync should run
        """
        from app.services.setting_service import SettingService
        
        # Get automatic sync settings
        setting_service = SettingService(self.db)
        auto_sync_enabled = setting_service.get_setting_value(
            'auto_sync', workspace_id=workspace_id, default_value=False
        )
        
        if not auto_sync_enabled:
            return False
            
        # Get sync time setting (hour of day)
        sync_hour = setting_service.get_setting_value(
            'sync_interval', workspace_id=workspace_id, default_value=9
        )
        
        # Check if we're in the right hour and haven't synced today
        from datetime import datetime, time
        current_time = datetime.now()
        
        # Check if it's the right hour (within 1 hour window)
        if current_time.hour != sync_hour:
            return False
            
        # Check if we've already done a daily sync today
        today = date.today()
        recent_sync = self.db.query(SyncLog).filter(
            SyncLog.workspace_id == workspace_id,
            SyncLog.sync_type == 'time_entries',
            SyncLog.status == 'completed',
            SyncLog.start_time >= datetime.combine(today, time.min),
            SyncLog.start_time <= datetime.combine(today, time.max)
        ).first()
        
        # If we already synced today, don't run again
        if recent_sync:
            return False
            
        return True
    
    def run_automatic_daily_sync(self, workspace_id: int) -> Optional[SyncLog]:
        """
        Run automatic daily sync if conditions are met.
        
        Args:
            workspace_id: Workspace ID to sync
            
        Returns:
            SyncLog if sync was run, None if skipped
        """
        if not self.should_run_automatic_sync(workspace_id):
            return None
            
        try:
            # Get daily sync recommendation
            recommendation = self.get_daily_sync_recommendation(workspace_id)
            
            if not recommendation['is_safe_for_free_plan']:
                self.logger.warning(
                    f"Skipping automatic sync for workspace {workspace_id}: "
                    f"Would exceed free plan limits ({recommendation['estimated_api_calls']} calls)"
                )
                return None
                
            # Run time entries only sync with recommended days
            sync_log = self.sync_time_entries_only(
                workspace_id, 
                recommendation['recommended_days']
            )
            
            self.logger.info(
                f"Automatic daily sync completed for workspace {workspace_id}: "
                f"{sync_log.records_added} added, {sync_log.records_updated} updated"
            )
            
            return sync_log
            
        except Exception as e:
            self.logger.error(f"Automatic daily sync failed for workspace {workspace_id}: {e}")
            return None


def get_sync_service(db: Session = Depends(get_db)) -> SyncService:
    """
    FastAPI dependency to get SyncService instance.
    
    Args:
        db: Database session from FastAPI dependency
        
    Returns:
        SyncService instance
    """
    config = TogglConfig.from_env()
    if config.api_token:
        toggl_client = TogglClient(api_token=config.api_token)
    else:
        toggl_client = TogglClient(email=config.email, password=config.password)
    
    return SyncService(db, toggl_client)