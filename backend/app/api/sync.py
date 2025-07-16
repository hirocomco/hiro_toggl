"""
API endpoints for data synchronization.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta
from pydantic import BaseModel, Field

from app.models.database import get_db
from app.services.sync_service import SyncService, get_sync_service
from app.models.models import SyncLog
from toggl_client import EnhancedTogglClient as TogglClient, TogglAPIError
from config.config.config import TogglConfig


router = APIRouter(prefix="/api/sync", tags=["sync"])


# Pydantic models for request/response
class SyncRequest(BaseModel):
    workspace_id: int
    sync_type: Optional[str] = Field(None, pattern="^(clients|projects|members|time_entries|full|metadata|time_entries_only)$")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    time_entries_days: Optional[int] = Field(30, ge=1, le=365)


class SyncLogResponse(BaseModel):
    id: int
    workspace_id: int
    sync_type: str
    status: str
    start_time: str
    end_time: Optional[str] = None
    records_processed: int
    records_added: int
    records_updated: int
    error_message: Optional[str] = None
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None

    class Config:
        from_attributes = True


class SyncStatusResponse(BaseModel):
    workspace_id: int
    recent_syncs: List[SyncLogResponse]
    last_full_sync: Optional[SyncLogResponse] = None
    is_sync_running: bool = False


def get_toggl_client() -> TogglClient:
    """Dependency to get configured Toggl client."""
    config = TogglConfig.from_env()
    
    if not config.is_valid():
        raise HTTPException(
            status_code=500,
            detail="Toggl API credentials not configured"
        )
    
    if config.api_token:
        return TogglClient(api_token=config.api_token)
    else:
        return TogglClient(email=config.email, password=config.password)


def sync_log_to_response(sync_log: SyncLog) -> SyncLogResponse:
    """Convert SyncLog model to response format."""
    return SyncLogResponse(
        id=sync_log.id,
        workspace_id=sync_log.workspace_id,
        sync_type=sync_log.sync_type,
        status=sync_log.status,
        start_time=sync_log.start_time.isoformat(),
        end_time=sync_log.end_time.isoformat() if sync_log.end_time else None,
        records_processed=sync_log.records_processed,
        records_added=sync_log.records_added,
        records_updated=sync_log.records_updated,
        error_message=sync_log.error_message,
        date_range_start=sync_log.date_range_start.isoformat() if sync_log.date_range_start else None,
        date_range_end=sync_log.date_range_end.isoformat() if sync_log.date_range_end else None
    )


async def run_sync_background(sync_service: SyncService, sync_request: SyncRequest):
    """Background task to run synchronization."""
    try:
        if sync_request.sync_type == "clients":
            sync_service.sync_clients(sync_request.workspace_id)
        elif sync_request.sync_type == "projects":
            sync_service.sync_projects(sync_request.workspace_id)
        elif sync_request.sync_type == "members":
            sync_service.sync_members(sync_request.workspace_id)
        elif sync_request.sync_type == "time_entries":
            start_date = sync_request.start_date or (date.today() - timedelta(days=sync_request.time_entries_days))
            end_date = sync_request.end_date or date.today()
            sync_service.sync_time_entries(sync_request.workspace_id, start_date, end_date)
        elif sync_request.sync_type == "full":
            sync_service.full_sync(sync_request.workspace_id, sync_request.time_entries_days)
        elif sync_request.sync_type == "metadata":
            sync_service.sync_metadata(sync_request.workspace_id)
        elif sync_request.sync_type == "time_entries_only":
            sync_service.sync_time_entries_only(sync_request.workspace_id, sync_request.time_entries_days)
    except Exception as e:
        # Log error - in a real application you'd want proper logging
        print(f"Background sync failed: {e}")


@router.post("/start", response_model=SyncLogResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_sync(
    sync_request: SyncRequest,
    background_tasks: BackgroundTasks,
    sync_service: SyncService = Depends(get_sync_service)
):
    """
    Start a data synchronization process.
    """
    try:
        # Validate sync type
        if not sync_request.sync_type:
            sync_request.sync_type = "full"
        
        # Check if there's already a running sync for this workspace
        recent_syncs = sync_service.get_sync_status(sync_request.workspace_id, limit=1)
        if recent_syncs and recent_syncs[0].status == 'running':
            raise HTTPException(
                status_code=409, 
                detail="A sync operation is already running for this workspace"
            )
        
        # Start the sync based on type
        if sync_request.sync_type == "clients":
            sync_log = sync_service.sync_clients(sync_request.workspace_id)
        elif sync_request.sync_type == "projects":
            sync_log = sync_service.sync_projects(sync_request.workspace_id)
        elif sync_request.sync_type == "members":
            sync_log = sync_service.sync_members(sync_request.workspace_id)
        elif sync_request.sync_type == "time_entries":
            start_date = sync_request.start_date or (date.today() - timedelta(days=sync_request.time_entries_days))
            end_date = sync_request.end_date or date.today()
            sync_log = sync_service.sync_time_entries(sync_request.workspace_id, start_date, end_date)
        elif sync_request.sync_type == "full":
            # For full sync, run in background and return the first sync log
            sync_logs = sync_service.full_sync(sync_request.workspace_id, sync_request.time_entries_days)
            sync_log = sync_logs[0] if sync_logs else None
        elif sync_request.sync_type == "metadata":
            # For metadata sync, run synchronously and return the first sync log
            sync_logs = sync_service.sync_metadata(sync_request.workspace_id)
            sync_log = sync_logs[0] if sync_logs else None
        elif sync_request.sync_type == "time_entries_only":
            # For time entries only sync, run synchronously
            sync_log = sync_service.sync_time_entries_only(sync_request.workspace_id, sync_request.time_entries_days)
        else:
            raise HTTPException(status_code=400, detail="Invalid sync type")
        
        if not sync_log:
            raise HTTPException(status_code=500, detail="Failed to start sync")
        
        return sync_log_to_response(sync_log)
        
    except TogglAPIError as e:
        raise HTTPException(status_code=400, detail=f"Toggl API error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start sync: {str(e)}")


@router.get("/status/{workspace_id}", response_model=SyncStatusResponse)
async def get_sync_status(
    workspace_id: int,
    sync_service: SyncService = Depends(get_sync_service)
):
    """
    Get synchronization status for a workspace.
    """
    try:
        recent_syncs = sync_service.get_sync_status(workspace_id, limit=10)
        
        # Convert to response format
        sync_responses = [sync_log_to_response(sync_log) for sync_log in recent_syncs]
        
        # Find last full sync
        last_full_sync = None
        for sync_log in recent_syncs:
            if sync_log.sync_type == 'full' and sync_log.status == 'completed':
                last_full_sync = sync_log_to_response(sync_log)
                break
        
        # Check if any sync is currently running
        is_sync_running = any(sync.status == 'running' for sync in recent_syncs)
        
        return SyncStatusResponse(
            workspace_id=workspace_id,
            recent_syncs=sync_responses,
            last_full_sync=last_full_sync,
            is_sync_running=is_sync_running
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sync status: {str(e)}")


@router.get("/logs/{workspace_id}", response_model=List[SyncLogResponse])
async def get_sync_logs(
    workspace_id: int,
    sync_type: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    sync_service: SyncService = Depends(get_sync_service)
):
    """
    Get synchronization logs for a workspace.
    """
    try:
        db = sync_service.db
        query = db.query(SyncLog).filter(SyncLog.workspace_id == workspace_id)
        
        if sync_type:
            query = query.filter(SyncLog.sync_type == sync_type)
        
        sync_logs = query.order_by(SyncLog.start_time.desc()).limit(limit).all()
        
        return [sync_log_to_response(sync_log) for sync_log in sync_logs]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sync logs: {str(e)}")


@router.post("/cleanup/{workspace_id}")
async def cleanup_old_data(
    workspace_id: int,
    days_to_keep: int = Query(90, ge=7, le=365),
    sync_service: SyncService = Depends(get_sync_service)
):
    """
    Clean up old cached time entries.
    """
    try:
        deleted_count = sync_service.cleanup_old_time_entries(workspace_id, days_to_keep)
        
        return {
            "workspace_id": workspace_id,
            "days_to_keep": days_to_keep,
            "deleted_records": deleted_count,
            "message": f"Cleaned up {deleted_count} old time entries"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup data: {str(e)}")


@router.get("/test/connection")
async def test_toggl_connection(
    toggl_client: TogglClient = Depends(get_toggl_client)
):
    """
    Test connection to Toggl API.
    """
    try:
        user = toggl_client.get_current_user()
        workspaces = toggl_client.get_workspaces()
        
        return {
            "status": "connected",
            "user": {
                "id": user.get("id"),
                "name": user.get("fullname"),
                "email": user.get("email")
            },
            "workspaces": [
                {
                    "id": w["id"],
                    "name": w["name"]
                }
                for w in workspaces
            ],
            "message": "Successfully connected to Toggl API"
        }
        
    except TogglAPIError as e:
        raise HTTPException(status_code=400, detail=f"Toggl API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")


@router.post("/force-sync/{workspace_id}")
async def force_full_sync(
    workspace_id: int,
    background_tasks: BackgroundTasks,
    time_entries_days: int = Query(30, ge=1, le=365),
    sync_service: SyncService = Depends(get_sync_service)
):
    """
    Force a full synchronization, even if one is already running.
    Use with caution - can cause duplicate data if multiple syncs run simultaneously.
    """
    try:
        # Run full sync
        sync_logs = sync_service.full_sync(workspace_id, time_entries_days)
        
        return {
            "workspace_id": workspace_id,
            "sync_logs": [sync_log_to_response(log) for log in sync_logs],
            "message": "Full sync completed"
        }
        
    except TogglAPIError as e:
        raise HTTPException(status_code=400, detail=f"Toggl API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Force sync failed: {str(e)}")


@router.get("/summary/{workspace_id}")
async def get_sync_summary(
    workspace_id: int,
    sync_service: SyncService = Depends(get_sync_service)
):
    """
    Get a summary of synchronized data for a workspace.
    """
    try:
        db = sync_service.db
        
        # Count records in each table
        from app.models.models import Client, Project, Member, TimeEntryCache
        
        clients_count = db.query(Client).filter(Client.workspace_id == workspace_id).count()
        projects_count = db.query(Project).filter(Project.workspace_id == workspace_id).count()
        members_count = db.query(Member).filter(Member.workspace_id == workspace_id).count()
        time_entries_count = db.query(TimeEntryCache).filter(TimeEntryCache.workspace_id == workspace_id).count()
        
        # Get latest sync times
        latest_syncs = {}
        for sync_type in ['clients', 'projects', 'members', 'time_entries']:
            latest_sync = db.query(SyncLog).filter(
                SyncLog.workspace_id == workspace_id,
                SyncLog.sync_type == sync_type,
                SyncLog.status == 'completed'
            ).order_by(SyncLog.end_time.desc()).first()
            
            latest_syncs[sync_type] = latest_sync.end_time.isoformat() if latest_sync else None
        
        return {
            "workspace_id": workspace_id,
            "data_counts": {
                "clients": clients_count,
                "projects": projects_count,
                "members": members_count,
                "time_entries": time_entries_count
            },
            "latest_sync_times": latest_syncs,
            "summary": f"Total: {clients_count} clients, {projects_count} projects, {members_count} members, {time_entries_count} time entries"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sync summary: {str(e)}")