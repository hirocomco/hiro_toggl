"""
Test routes for validating the Toggl API integration.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import os
from datetime import datetime, timedelta

from toggl_client import EnhancedTogglClient as TogglClient, MemberTimeTotal, TogglAPIError
from config import TogglConfig

router = APIRouter(prefix="/api/test", tags=["test"])


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


@router.get("/connection")
async def test_connection(client: TogglClient = Depends(get_toggl_client)):
    """Test connection to Toggl API."""
    try:
        user = client.get_current_user()
        workspaces = client.get_workspaces()
        
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
            ]
        }
    except TogglAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/clients/{workspace_id}")
async def test_get_clients(
    workspace_id: int,
    client: TogglClient = Depends(get_toggl_client)
):
    """Test getting clients for a workspace."""
    try:
        clients = client.get_workspace_clients(workspace_id)
        return {
            "workspace_id": workspace_id,
            "clients": [
                {
                    "id": c.id,
                    "name": c.name,
                    "archived": c.archived
                }
                for c in clients
            ]
        }
    except TogglAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects/{workspace_id}")
async def test_get_projects(
    workspace_id: int,
    client: TogglClient = Depends(get_toggl_client)
):
    """Test getting projects for a workspace."""
    try:
        projects = client.get_workspace_projects(workspace_id)
        return {
            "workspace_id": workspace_id,
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "client_id": p.client_id,
                    "billable": p.billable,
                    "active": p.active
                }
                for p in projects
            ]
        }
    except TogglAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/time-entries/{workspace_id}")
async def test_get_time_entries(
    workspace_id: int,
    days: int = 7,
    client: TogglClient = Depends(get_toggl_client)
):
    """Test getting time entries with client information."""
    try:
        # Get time entries for the last N days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        time_entries = client.get_workspace_time_entries_with_clients(
            workspace_id,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        return {
            "workspace_id": workspace_id,
            "date_range": {
                "start": start_date.strftime('%Y-%m-%d'),
                "end": end_date.strftime('%Y-%m-%d')
            },
            "total_entries": len(time_entries),
            "entries": [
                {
                    "id": entry.id,
                    "description": entry.description,
                    "duration_hours": round(entry.duration / 3600, 2),
                    "user_name": entry.user_name,
                    "project_name": entry.project_name,
                    "client_name": entry.client_name,
                    "billable": entry.billable
                }
                for entry in time_entries[:10]  # Show first 10 entries
            ]
        }
    except TogglAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/client-reports/{workspace_id}")
async def test_client_reports(
    workspace_id: int,
    days: int = 30,
    client: TogglClient = Depends(get_toggl_client)
):
    """Test generating client reports."""
    try:
        # Get reports for the last N days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        reports = client.generate_client_reports(
            workspace_id,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        return {
            "workspace_id": workspace_id,
            "date_range": {
                "start": start_date.strftime('%Y-%m-%d'),
                "end": end_date.strftime('%Y-%m-%d')
            },
            "total_clients": len(reports),
            "reports": [
                {
                    "client_id": report.client_id,
                    "client_name": report.client_name,
                    "total_hours": round(report.total_hours, 2),
                    "billable_hours": round(report.billable_hours, 2),
                    "members": [
                        {
                            "user_name": member.user_name,
                            "total_hours": round(member.total_hours, 2),
                            "billable_hours": round(member.billable_hours, 2),
                            "entry_count": member.entry_count
                        }
                        for member in report.member_reports
                    ]
                }
                for report in reports
            ]
        }
    except TogglAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))