"""
API endpoints for client reports and financial analytics.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import logging

from app.models.database import get_db
from app.services.report_service import ReportService, get_report_service
from app.schemas.reports import (
    ClientReportRequest, MemberReportRequest, ReportExportRequest, DrillDownRequest,
    WorkspaceReportResponse, ClientDetailResponse, MemberPerformanceResponse,
    DrillDownResponse, ReportPeriod, ReportTotals, ClientReportData, MemberReportData,
    ProjectReportData, TimeEntryDetail
)
from app.utils.date_helpers import get_date_range_for_period, format_date_range_description
from app.models.models import TimeEntryCache, Member, Client


router = APIRouter(prefix="/api/reports", tags=["reports"])
logger = logging.getLogger(__name__)


@router.post("/workspace", response_model=WorkspaceReportResponse)
async def generate_workspace_report(
    request: ClientReportRequest,
    report_service: ReportService = Depends(get_report_service)
):
    """
    Generate comprehensive workspace report with client breakdowns.
    """
    try:
        # Calculate date range
        start_date, end_date = get_date_range_for_period(
            request.period, request.start_date, request.end_date
        )
        
        logger.info(f"Generating workspace report for workspace {request.workspace_id}, {start_date} to {end_date}")
        
        # Generate report
        report_data = report_service.generate_client_reports(
            workspace_id=request.workspace_id,
            start_date=start_date,
            end_date=end_date,
            client_ids=request.client_ids,
            member_ids=request.member_ids,
            include_non_billable=request.include_non_billable,
            include_financial=request.include_financial
        )
        
        # Convert to response format
        client_reports = []
        for client_data in report_data.client_reports:
            member_reports = []
            for member_data in client_data.member_reports:
                member_reports.append(MemberReportData(
                    member_id=member_data.member_id,
                    member_name=member_data.member_name,
                    total_hours=member_data.total_hours,
                    billable_hours=member_data.billable_hours,
                    entry_count=member_data.entry_count,
                    total_earnings_usd=float(member_data.total_earnings_usd) if member_data.total_earnings_usd else None,
                    total_earnings_eur=float(member_data.total_earnings_eur) if member_data.total_earnings_eur else None,
                    billable_earnings_usd=float(member_data.billable_earnings_usd) if member_data.billable_earnings_usd else None,
                    billable_earnings_eur=float(member_data.billable_earnings_eur) if member_data.billable_earnings_eur else None,
                    hourly_rate_usd=float(member_data.hourly_rate_usd) if member_data.hourly_rate_usd else None,
                    hourly_rate_eur=float(member_data.hourly_rate_eur) if member_data.hourly_rate_eur else None
                ))
            
            client_reports.append(ClientReportData(
                client_id=client_data.client_id,
                client_name=client_data.client_name,
                total_hours=client_data.total_hours,
                billable_hours=client_data.billable_hours,
                total_earnings_usd=float(client_data.total_earnings_usd) if client_data.total_earnings_usd else None,
                total_earnings_eur=float(client_data.total_earnings_eur) if client_data.total_earnings_eur else None,
                billable_earnings_usd=float(client_data.billable_earnings_usd) if client_data.billable_earnings_usd else None,
                billable_earnings_eur=float(client_data.billable_earnings_eur) if client_data.billable_earnings_eur else None,
                project_count=client_data.project_count,
                member_reports=member_reports
            ))
        
        # Sort client reports if requested
        if request.sort_by == "client_name":
            reverse_order = request.sort_order == "desc"
            client_reports.sort(key=lambda c: c.client_name.lower(), reverse=reverse_order)
        elif request.sort_by == "total_hours":
            reverse_order = request.sort_order == "desc"
            client_reports.sort(key=lambda c: c.total_hours, reverse=reverse_order)
        elif request.sort_by == "billable_hours":
            reverse_order = request.sort_order == "desc"
            client_reports.sort(key=lambda c: c.billable_hours, reverse=reverse_order)
        elif request.sort_by == "total_earnings_usd" and request.include_financial:
            reverse_order = request.sort_order == "desc"
            client_reports.sort(key=lambda c: c.total_earnings_usd or 0, reverse=reverse_order)
        elif request.sort_by == "total_earnings_eur" and request.include_financial:
            reverse_order = request.sort_order == "desc"
            client_reports.sort(key=lambda c: c.total_earnings_eur or 0, reverse=reverse_order)
        
        return WorkspaceReportResponse(
            workspace_id=request.workspace_id,
            date_range={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "description": format_date_range_description(start_date, end_date)
            },
            totals=ReportTotals(
                total_hours=report_data.total_hours,
                billable_hours=report_data.billable_hours,
                entry_count=sum(len(c.member_reports) for c in report_data.client_reports),
                total_earnings_usd=float(report_data.total_earnings_usd) if report_data.total_earnings_usd else None,
                total_earnings_eur=float(report_data.total_earnings_eur) if report_data.total_earnings_eur else None,
                billable_earnings_usd=float(report_data.billable_earnings_usd) if report_data.billable_earnings_usd else None,
                billable_earnings_eur=float(report_data.billable_earnings_eur) if report_data.billable_earnings_eur else None
            ),
            summary={
                "total_clients": report_data.total_clients,
                "total_members": report_data.total_members,
                "total_projects": report_data.total_projects,
                "clients_with_time": len(client_reports)
            },
            client_reports=client_reports,
            generated_at=datetime.utcnow()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate workspace report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/client/{client_id}", response_model=ClientDetailResponse)
async def get_client_detail_report(
    client_id: Optional[int],
    workspace_id: int = Query(..., description="Workspace ID"),
    period: ReportPeriod = Query(ReportPeriod.LAST_30_DAYS),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    include_project_breakdown: bool = Query(True),
    report_service: ReportService = Depends(get_report_service)
):
    """
    Get detailed report for a specific client.
    Use client_id=null or 0 for "No Client" entries.
    """
    try:
        # Handle "No Client" case
        if client_id == 0:
            client_id = None
        
        # Calculate date range
        start_date, end_date = get_date_range_for_period(period, start_date, end_date)
        
        logger.info(f"Generating client detail report for client {client_id}, workspace {workspace_id}")
        
        # Generate detailed client report
        report_data = report_service.get_client_detail_report(
            workspace_id=workspace_id,
            client_id=client_id,
            start_date=start_date,
            end_date=end_date,
            include_project_breakdown=include_project_breakdown
        )
        
        # Convert project data to response format
        projects = []
        if include_project_breakdown:
            for project_data in report_data.get('projects', []):
                members = []
                for member_data in project_data.get('members', []):
                    members.append(MemberReportData(
                        member_id=member_data['member_id'],
                        member_name=member_data['member_name'],
                        total_hours=member_data['total_hours'],
                        billable_hours=member_data['billable_hours'],
                        entry_count=member_data['entry_count'],
                        total_earnings_usd=member_data['total_earnings_usd'],
                        total_earnings_eur=member_data['total_earnings_eur'],
                        billable_earnings_usd=member_data['billable_earnings_usd'],
                        billable_earnings_eur=member_data['billable_earnings_eur']
                    ))
                
                projects.append(ProjectReportData(
                    project_id=project_data['project_id'],
                    project_name=project_data['project_name'],
                    total_hours=project_data['total_hours'],
                    billable_hours=project_data['billable_hours'],
                    entry_count=project_data['entry_count'],
                    total_earnings_usd=project_data['total_earnings_usd'],
                    total_earnings_eur=project_data['total_earnings_eur'],
                    billable_earnings_usd=project_data['billable_earnings_usd'],
                    billable_earnings_eur=project_data['billable_earnings_eur'],
                    members=members
                ))
        
        totals_data = report_data['totals']
        
        return ClientDetailResponse(
            client_id=client_id,
            client_name=report_data['client_name'],
            workspace_id=workspace_id,
            date_range={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "description": format_date_range_description(start_date, end_date)
            },
            totals=ReportTotals(
                total_hours=totals_data['total_hours'],
                billable_hours=totals_data['billable_hours'],
                entry_count=totals_data['entry_count'],
                total_earnings_usd=totals_data['total_earnings_usd'],
                total_earnings_eur=totals_data['total_earnings_eur'],
                billable_earnings_usd=totals_data['billable_earnings_usd'],
                billable_earnings_eur=totals_data['billable_earnings_eur']
            ),
            projects=projects,
            generated_at=datetime.utcnow()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate client detail report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate client report: {str(e)}")


@router.get("/member/{member_id}", response_model=MemberPerformanceResponse)
async def get_member_performance_report(
    member_id: int,
    workspace_id: int = Query(..., description="Workspace ID"),
    period: ReportPeriod = Query(ReportPeriod.LAST_30_DAYS),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    report_service: ReportService = Depends(get_report_service)
):
    """
    Get performance report for a specific member.
    """
    try:
        # Calculate date range
        start_date, end_date = get_date_range_for_period(period, start_date, end_date)
        
        logger.info(f"Generating member performance report for member {member_id}, workspace {workspace_id}")
        
        # Generate member performance report
        report_data = report_service.get_member_performance_report(
            workspace_id=workspace_id,
            member_id=member_id,
            start_date=start_date,
            end_date=end_date
        )
        
        totals_data = report_data['totals']
        
        return MemberPerformanceResponse(
            member_id=member_id,
            member_name=report_data['member_name'],
            workspace_id=workspace_id,
            date_range={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "description": format_date_range_description(start_date, end_date)
            },
            totals=ReportTotals(
                total_hours=totals_data['total_hours'],
                billable_hours=totals_data['billable_hours'],
                entry_count=totals_data['entry_count'],
                total_earnings_usd=totals_data['total_earnings_usd'],
                total_earnings_eur=totals_data['total_earnings_eur'],
                billable_earnings_usd=totals_data['billable_earnings_usd'],
                billable_earnings_eur=totals_data['billable_earnings_eur']
            ),
            clients=report_data['clients'],
            generated_at=datetime.utcnow()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate member performance report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate member report: {str(e)}")


@router.post("/drill-down", response_model=DrillDownResponse)
async def get_drill_down_report(
    request: DrillDownRequest,
    db: Session = Depends(get_db)
):
    """
    Get detailed time entry drill-down report with filtering and pagination.
    """
    try:
        # Calculate date range
        start_date = request.start_date or (date.today() - timedelta(days=30))
        end_date = request.end_date or date.today()
        
        logger.info(f"Generating drill-down report for workspace {request.workspace_id}")
        
        # Build base query
        query = db.query(TimeEntryCache).filter(
            TimeEntryCache.workspace_id == request.workspace_id,
            TimeEntryCache.start_time >= datetime.combine(start_date, datetime.min.time()),
            TimeEntryCache.start_time <= datetime.combine(end_date, datetime.max.time()),
            TimeEntryCache.duration > 0
        )
        
        # Apply filters
        if request.client_id is not None:
            if request.client_id == 0:
                query = query.filter(TimeEntryCache.client_id.is_(None))
            else:
                query = query.filter(TimeEntryCache.client_id == request.client_id)
        
        if request.member_id:
            query = query.filter(TimeEntryCache.user_id == request.member_id)
        
        if request.project_id:
            if request.project_id == 0:
                query = query.filter(TimeEntryCache.project_id.is_(None))
            else:
                query = query.filter(TimeEntryCache.project_id == request.project_id)
        
        if request.billable_only:
            query = query.filter(TimeEntryCache.billable == True)
        
        # Get total count for pagination
        total_entries = query.count()
        
        # Apply sorting
        if request.sort_by == "start_time":
            if request.sort_order == "desc":
                query = query.order_by(TimeEntryCache.start_time.desc())
            else:
                query = query.order_by(TimeEntryCache.start_time.asc())
        elif request.sort_by == "duration":
            if request.sort_order == "desc":
                query = query.order_by(TimeEntryCache.duration.desc())
            else:
                query = query.order_by(TimeEntryCache.duration.asc())
        elif request.sort_by == "description":
            if request.sort_order == "desc":
                query = query.order_by(TimeEntryCache.description.desc())
            else:
                query = query.order_by(TimeEntryCache.description.asc())
        elif request.sort_by == "user_name":
            if request.sort_order == "desc":
                query = query.order_by(TimeEntryCache.user_name.desc())
            else:
                query = query.order_by(TimeEntryCache.user_name.asc())
        elif request.sort_by == "project_name":
            if request.sort_order == "desc":
                query = query.order_by(TimeEntryCache.project_name.desc())
            else:
                query = query.order_by(TimeEntryCache.project_name.asc())
        elif request.sort_by == "client_name":
            if request.sort_order == "desc":
                query = query.order_by(TimeEntryCache.client_name.desc())
            else:
                query = query.order_by(TimeEntryCache.client_name.asc())
        
        # Apply pagination
        time_entries = query.offset(request.offset).limit(request.limit).all()
        
        # Calculate summary for filtered results
        summary_query = db.query(TimeEntryCache).filter(
            TimeEntryCache.workspace_id == request.workspace_id,
            TimeEntryCache.start_time >= datetime.combine(start_date, datetime.min.time()),
            TimeEntryCache.start_time <= datetime.combine(end_date, datetime.max.time()),
            TimeEntryCache.duration > 0
        )
        
        # Apply same filters for summary
        if request.client_id is not None:
            if request.client_id == 0:
                summary_query = summary_query.filter(TimeEntryCache.client_id.is_(None))
            else:
                summary_query = summary_query.filter(TimeEntryCache.client_id == request.client_id)
        
        if request.member_id:
            summary_query = summary_query.filter(TimeEntryCache.user_id == request.member_id)
        
        if request.project_id:
            if request.project_id == 0:
                summary_query = summary_query.filter(TimeEntryCache.project_id.is_(None))
            else:
                summary_query = summary_query.filter(TimeEntryCache.project_id == request.project_id)
        
        if request.billable_only:
            summary_query = summary_query.filter(TimeEntryCache.billable == True)
        
        # Calculate summary totals
        all_entries = summary_query.all()
        total_duration = sum(entry.duration for entry in all_entries)
        billable_duration = sum(entry.duration for entry in all_entries if entry.billable)
        
        # Convert to response format
        entries = []
        for entry in time_entries:
            entries.append(TimeEntryDetail(
                id=entry.toggl_id,
                description=entry.description or "",
                duration_hours=round(entry.duration / 3600, 2),
                start_time=entry.start_time,
                stop_time=entry.stop_time,
                user_name=entry.user_name or "",
                project_name=entry.project_name or "No Project",
                client_name=entry.client_name or "No Client",
                billable=entry.billable,
                tags=entry.tags or []
            ))
        
        # Calculate pagination info
        total_pages = (total_entries + request.limit - 1) // request.limit
        
        return DrillDownResponse(
            workspace_id=request.workspace_id,
            filters={
                "client_id": request.client_id,
                "member_id": request.member_id,
                "project_id": request.project_id,
                "billable_only": request.billable_only,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            total_entries=total_entries,
            entries=entries,
            pagination={
                "limit": request.limit,
                "offset": request.offset,
                "total_pages": total_pages,
                "current_page": (request.offset // request.limit) + 1
            },
            summary=ReportTotals(
                total_hours=round(total_duration / 3600, 2),
                billable_hours=round(billable_duration / 3600, 2),
                entry_count=len(all_entries),
                total_earnings_usd=None,  # Would need rate calculations
                total_earnings_eur=None,
                billable_earnings_usd=None,
                billable_earnings_eur=None
            ),
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to generate drill-down report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate drill-down report: {str(e)}")


@router.get("/summary/{workspace_id}")
async def get_report_summary(
    workspace_id: int,
    period: ReportPeriod = Query(ReportPeriod.LAST_30_DAYS),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get quick summary statistics for reports dashboard.
    """
    try:
        # Calculate date range
        start_date, end_date = get_date_range_for_period(period, start_date, end_date)
        
        # Get basic counts
        total_clients = db.query(Client).filter(Client.workspace_id == workspace_id).count()
        total_members = db.query(Member).filter(Member.workspace_id == workspace_id).count()
        
        # Get time entry statistics
        time_entries = db.query(TimeEntryCache).filter(
            TimeEntryCache.workspace_id == workspace_id,
            TimeEntryCache.start_time >= datetime.combine(start_date, datetime.min.time()),
            TimeEntryCache.start_time <= datetime.combine(end_date, datetime.max.time()),
            TimeEntryCache.duration > 0
        ).all()
        
        total_duration = sum(entry.duration for entry in time_entries)
        billable_duration = sum(entry.duration for entry in time_entries if entry.billable)
        
        # Get unique clients and members with time entries
        clients_with_time = len(set(entry.client_id for entry in time_entries))
        members_with_time = len(set(entry.user_id for entry in time_entries))
        
        return {
            "workspace_id": workspace_id,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "description": format_date_range_description(start_date, end_date)
            },
            "totals": {
                "total_hours": round(total_duration / 3600, 2),
                "billable_hours": round(billable_duration / 3600, 2),
                "total_entries": len(time_entries),
                "billable_percentage": round((billable_duration / total_duration) * 100, 1) if total_duration > 0 else 0
            },
            "counts": {
                "total_clients": total_clients,
                "total_members": total_members,
                "clients_with_time": clients_with_time,
                "members_with_time": members_with_time
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to generate report summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


@router.get("/clients/{workspace_id}")
async def get_clients_for_reports(
    workspace_id: int,
    include_no_client: bool = Query(True, description="Include 'No Client' option"),
    db: Session = Depends(get_db)
):
    """
    Get list of clients for report filtering dropdowns.
    """
    try:
        clients = db.query(Client).filter(
            Client.workspace_id == workspace_id,
            Client.archived == False
        ).order_by(Client.name).all()
        
        client_list = []
        
        if include_no_client:
            client_list.append({
                "id": None,
                "name": "No Client",
                "toggl_id": None
            })
        
        for client in clients:
            client_list.append({
                "id": client.id,
                "name": client.name,
                "toggl_id": client.toggl_id
            })
        
        return {
            "workspace_id": workspace_id,
            "clients": client_list,
            "total_count": len(client_list)
        }
        
    except Exception as e:
        logger.error(f"Failed to get clients for reports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get clients: {str(e)}")


@router.get("/members/{workspace_id}")
async def get_members_for_reports(
    workspace_id: int,
    db: Session = Depends(get_db)
):
    """
    Get list of members for report filtering dropdowns.
    """
    try:
        members = db.query(Member).filter(
            Member.workspace_id == workspace_id,
            Member.active == True
        ).order_by(Member.name).all()
        
        member_list = []
        for member in members:
            member_list.append({
                "id": member.id,
                "name": member.name,
                "toggl_id": member.toggl_id,
                "email": member.email
            })
        
        return {
            "workspace_id": workspace_id,
            "members": member_list,
            "total_count": len(member_list)
        }
        
    except Exception as e:
        logger.error(f"Failed to get members for reports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get members: {str(e)}")