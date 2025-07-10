"""
Report generation service for client-based reports with financial calculations.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text
from typing import List, Optional, Dict, Any, Tuple
from datetime import date, datetime, timedelta
from decimal import Decimal
import logging
from dataclasses import dataclass
from fastapi import Depends

from app.models.models import (
    Client, Project, Member, TimeEntryCache, Rate, SyncLog
)
from app.models.database import get_db
from app.services.rate_service import RateService


@dataclass
class MemberReportData:
    """Data class for member report information."""
    member_id: int
    member_name: str
    total_duration_seconds: int
    billable_duration_seconds: int
    entry_count: int
    total_earnings_usd: Optional[Decimal] = None
    total_earnings_eur: Optional[Decimal] = None
    billable_earnings_usd: Optional[Decimal] = None
    billable_earnings_eur: Optional[Decimal] = None
    hourly_rate_usd: Optional[Decimal] = None
    hourly_rate_eur: Optional[Decimal] = None
    
    @property
    def total_hours(self) -> float:
        """Get total duration in hours."""
        return self.total_duration_seconds / 3600.0
    
    @property
    def billable_hours(self) -> float:
        """Get billable duration in hours."""
        return self.billable_duration_seconds / 3600.0


@dataclass
class ClientReportData:
    """Data class for client report information."""
    client_id: Optional[int]
    client_name: str
    total_duration_seconds: int
    billable_duration_seconds: int
    total_earnings_usd: Optional[Decimal] = None
    total_earnings_eur: Optional[Decimal] = None
    billable_earnings_usd: Optional[Decimal] = None
    billable_earnings_eur: Optional[Decimal] = None
    member_reports: List[MemberReportData] = None
    project_count: int = 0
    
    def __post_init__(self):
        if self.member_reports is None:
            self.member_reports = []
    
    @property
    def total_hours(self) -> float:
        """Get total duration in hours."""
        return self.total_duration_seconds / 3600.0
    
    @property
    def billable_hours(self) -> float:
        """Get billable duration in hours."""
        return self.billable_duration_seconds / 3600.0


@dataclass
class WorkspaceReportSummary:
    """Data class for workspace report summary."""
    workspace_id: int
    total_clients: int
    total_members: int
    total_projects: int
    date_range_start: date
    date_range_end: date
    total_duration_seconds: int
    billable_duration_seconds: int
    total_earnings_usd: Optional[Decimal] = None
    total_earnings_eur: Optional[Decimal] = None
    billable_earnings_usd: Optional[Decimal] = None
    billable_earnings_eur: Optional[Decimal] = None
    client_reports: List[ClientReportData] = None
    
    def __post_init__(self):
        if self.client_reports is None:
            self.client_reports = []
    
    @property
    def total_hours(self) -> float:
        """Get total duration in hours."""
        return self.total_duration_seconds / 3600.0
    
    @property
    def billable_hours(self) -> float:
        """Get billable duration in hours."""
        return self.billable_duration_seconds / 3600.0


class ReportService:
    """Service for generating client-based reports with financial calculations."""

    def __init__(self, db: Session):
        self.db = db
        self.rate_service = RateService(db)
        self.logger = logging.getLogger(__name__)

    def generate_client_reports(
        self,
        workspace_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        client_ids: Optional[List[int]] = None,
        member_ids: Optional[List[int]] = None,
        include_non_billable: bool = True,
        include_financial: bool = True
    ) -> WorkspaceReportSummary:
        """
        Generate comprehensive client reports with member breakdowns and financial calculations.
        
        Args:
            workspace_id: Workspace ID
            start_date: Start date for report (defaults to 30 days ago)
            end_date: End date for report (defaults to today)
            client_ids: Specific client IDs to include (None for all)
            member_ids: Specific member IDs to include (None for all)
            include_non_billable: Include non-billable time
            include_financial: Calculate financial totals
            
        Returns:
            WorkspaceReportSummary with client and member breakdowns
        """
        # Set default date range
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        self.logger.info(f"Generating client reports for workspace {workspace_id}, {start_date} to {end_date}")

        # Build base query for time entries
        query = self.db.query(TimeEntryCache).filter(
            and_(
                TimeEntryCache.workspace_id == workspace_id,
                TimeEntryCache.start_time >= datetime.combine(start_date, datetime.min.time()),
                TimeEntryCache.start_time <= datetime.combine(end_date, datetime.max.time()),
                TimeEntryCache.duration > 0  # Only positive durations
            )
        )

        # Apply filters
        if client_ids:
            query = query.filter(TimeEntryCache.client_id.in_(client_ids))
        
        if member_ids:
            query = query.filter(TimeEntryCache.user_id.in_(member_ids))

        if not include_non_billable:
            query = query.filter(TimeEntryCache.billable == True)

        # Get all time entries
        time_entries = query.all()

        # Group entries by client and member
        client_data = {}
        workspace_totals = {
            'total_duration': 0,
            'billable_duration': 0,
            'total_earnings_usd': Decimal('0'),
            'total_earnings_eur': Decimal('0'),
            'billable_earnings_usd': Decimal('0'),
            'billable_earnings_eur': Decimal('0')
        }

        for entry in time_entries:
            client_key = entry.client_id or 'no_client'
            client_name = entry.client_name or 'No Client'
            
            # Initialize client data if not exists
            if client_key not in client_data:
                client_data[client_key] = {
                    'client_id': entry.client_id,
                    'client_name': client_name,
                    'total_duration': 0,
                    'billable_duration': 0,
                    'total_earnings_usd': Decimal('0'),
                    'total_earnings_eur': Decimal('0'),
                    'billable_earnings_usd': Decimal('0'),
                    'billable_earnings_eur': Decimal('0'),
                    'members': {},
                    'project_ids': set()
                }

            # Add to client totals
            client_data[client_key]['total_duration'] += entry.duration
            client_data[client_key]['project_ids'].add(entry.project_id)
            
            if entry.billable:
                client_data[client_key]['billable_duration'] += entry.duration

            # Add to workspace totals
            workspace_totals['total_duration'] += entry.duration
            if entry.billable:
                workspace_totals['billable_duration'] += entry.duration

            # Initialize member data within client
            member_key = entry.user_id
            if member_key not in client_data[client_key]['members']:
                client_data[client_key]['members'][member_key] = {
                    'member_id': entry.user_id,
                    'member_name': entry.user_name,
                    'total_duration': 0,
                    'billable_duration': 0,
                    'entry_count': 0,
                    'total_earnings_usd': Decimal('0'),
                    'total_earnings_eur': Decimal('0'),
                    'billable_earnings_usd': Decimal('0'),
                    'billable_earnings_eur': Decimal('0'),
                    'hourly_rate_usd': None,
                    'hourly_rate_eur': None
                }

            # Add to member totals
            member_data = client_data[client_key]['members'][member_key]
            member_data['total_duration'] += entry.duration
            member_data['entry_count'] += 1
            
            if entry.billable:
                member_data['billable_duration'] += entry.duration

            # Calculate financial data if requested
            if include_financial:
                # Get member's database ID for rate lookup
                member_db = self.db.query(Member).filter(Member.toggl_id == entry.user_id).first()
                if member_db:
                    # Get rate for this member and client
                    work_date = entry.start_time.date()
                    client_db_id = None
                    if entry.client_id:
                        client_db = self.db.query(Client).filter(Client.toggl_id == entry.client_id).first()
                        if client_db:
                            client_db_id = client_db.id

                    rate = self.rate_service.get_member_rate(member_db.id, client_db_id, work_date)
                    
                    if rate:
                        # Store hourly rates for display
                        if member_data['hourly_rate_usd'] is None:
                            member_data['hourly_rate_usd'] = rate.hourly_rate_usd
                            member_data['hourly_rate_eur'] = rate.hourly_rate_eur

                        # Calculate earnings
                        if rate.hourly_rate_usd:
                            hours = Decimal(entry.duration) / Decimal(3600)
                            earnings_usd = hours * rate.hourly_rate_usd
                            
                            member_data['total_earnings_usd'] += earnings_usd
                            client_data[client_key]['total_earnings_usd'] += earnings_usd
                            workspace_totals['total_earnings_usd'] += earnings_usd
                            
                            if entry.billable:
                                member_data['billable_earnings_usd'] += earnings_usd
                                client_data[client_key]['billable_earnings_usd'] += earnings_usd
                                workspace_totals['billable_earnings_usd'] += earnings_usd

                        if rate.hourly_rate_eur:
                            hours = Decimal(entry.duration) / Decimal(3600)
                            earnings_eur = hours * rate.hourly_rate_eur
                            
                            member_data['total_earnings_eur'] += earnings_eur
                            client_data[client_key]['total_earnings_eur'] += earnings_eur
                            workspace_totals['total_earnings_eur'] += earnings_eur
                            
                            if entry.billable:
                                member_data['billable_earnings_eur'] += earnings_eur
                                client_data[client_key]['billable_earnings_eur'] += earnings_eur
                                workspace_totals['billable_earnings_eur'] += earnings_eur

        # Convert to report data structures
        client_reports = []
        for client_info in client_data.values():
            # Create member reports
            member_reports = []
            for member_info in client_info['members'].values():
                member_reports.append(MemberReportData(
                    member_id=member_info['member_id'],
                    member_name=member_info['member_name'],
                    total_duration_seconds=member_info['total_duration'],
                    billable_duration_seconds=member_info['billable_duration'],
                    entry_count=member_info['entry_count'],
                    total_earnings_usd=member_info['total_earnings_usd'] if include_financial else None,
                    total_earnings_eur=member_info['total_earnings_eur'] if include_financial else None,
                    billable_earnings_usd=member_info['billable_earnings_usd'] if include_financial else None,
                    billable_earnings_eur=member_info['billable_earnings_eur'] if include_financial else None,
                    hourly_rate_usd=member_info['hourly_rate_usd'],
                    hourly_rate_eur=member_info['hourly_rate_eur']
                ))

            # Sort members by total hours descending
            member_reports.sort(key=lambda m: m.total_hours, reverse=True)

            # Create client report
            client_reports.append(ClientReportData(
                client_id=client_info['client_id'],
                client_name=client_info['client_name'],
                total_duration_seconds=client_info['total_duration'],
                billable_duration_seconds=client_info['billable_duration'],
                total_earnings_usd=client_info['total_earnings_usd'] if include_financial else None,
                total_earnings_eur=client_info['total_earnings_eur'] if include_financial else None,
                billable_earnings_usd=client_info['billable_earnings_usd'] if include_financial else None,
                billable_earnings_eur=client_info['billable_earnings_eur'] if include_financial else None,
                member_reports=member_reports,
                project_count=len(client_info['project_ids'])
            ))

        # Sort clients by total hours descending
        client_reports.sort(key=lambda c: c.total_hours, reverse=True)

        # Get workspace counts
        total_clients = self.db.query(Client).filter(Client.workspace_id == workspace_id).count()
        total_members = self.db.query(Member).filter(Member.workspace_id == workspace_id).count()
        total_projects = self.db.query(Project).filter(Project.workspace_id == workspace_id).count()

        # Create workspace summary
        return WorkspaceReportSummary(
            workspace_id=workspace_id,
            total_clients=total_clients,
            total_members=total_members,
            total_projects=total_projects,
            date_range_start=start_date,
            date_range_end=end_date,
            total_duration_seconds=workspace_totals['total_duration'],
            billable_duration_seconds=workspace_totals['billable_duration'],
            total_earnings_usd=workspace_totals['total_earnings_usd'] if include_financial else None,
            total_earnings_eur=workspace_totals['total_earnings_eur'] if include_financial else None,
            billable_earnings_usd=workspace_totals['billable_earnings_usd'] if include_financial else None,
            billable_earnings_eur=workspace_totals['billable_earnings_eur'] if include_financial else None,
            client_reports=client_reports
        )

    def get_client_detail_report(
        self,
        workspace_id: int,
        client_id: Optional[int],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_project_breakdown: bool = True
    ) -> Dict[str, Any]:
        """
        Get detailed report for a specific client including project breakdown.
        
        Args:
            workspace_id: Workspace ID
            client_id: Client ID (None for "No Client")
            start_date: Start date for report
            end_date: End date for report
            include_project_breakdown: Include project-level breakdown
            
        Returns:
            Detailed client report with project and member breakdowns
        """
        # Set default date range
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        # Get client info
        client_name = "No Client"
        if client_id:
            client = self.db.query(Client).filter(Client.toggl_id == client_id).first()
            if client:
                client_name = client.name

        # Base query for time entries
        query = self.db.query(TimeEntryCache).filter(
            and_(
                TimeEntryCache.workspace_id == workspace_id,
                TimeEntryCache.start_time >= datetime.combine(start_date, datetime.min.time()),
                TimeEntryCache.start_time <= datetime.combine(end_date, datetime.max.time()),
                TimeEntryCache.duration > 0
            )
        )

        # Filter by client
        if client_id:
            query = query.filter(TimeEntryCache.client_id == client_id)
        else:
            query = query.filter(TimeEntryCache.client_id.is_(None))

        time_entries = query.all()

        # Group by project and member
        project_data = {}
        client_totals = {
            'total_duration': 0,
            'billable_duration': 0,
            'entry_count': 0,
            'total_earnings_usd': Decimal('0'),
            'total_earnings_eur': Decimal('0'),
            'billable_earnings_usd': Decimal('0'),
            'billable_earnings_eur': Decimal('0')
        }

        for entry in time_entries:
            project_key = entry.project_id or 'no_project'
            project_name = entry.project_name or 'No Project'

            # Initialize project data
            if project_key not in project_data:
                project_data[project_key] = {
                    'project_id': entry.project_id,
                    'project_name': project_name,
                    'total_duration': 0,
                    'billable_duration': 0,
                    'entry_count': 0,
                    'total_earnings_usd': Decimal('0'),
                    'total_earnings_eur': Decimal('0'),
                    'billable_earnings_usd': Decimal('0'),
                    'billable_earnings_eur': Decimal('0'),
                    'members': {}
                }

            # Add to project totals
            project_data[project_key]['total_duration'] += entry.duration
            project_data[project_key]['entry_count'] += 1
            if entry.billable:
                project_data[project_key]['billable_duration'] += entry.duration

            # Add to client totals
            client_totals['total_duration'] += entry.duration
            client_totals['entry_count'] += 1
            if entry.billable:
                client_totals['billable_duration'] += entry.duration

            # Handle member data within project
            member_key = entry.user_id
            if member_key not in project_data[project_key]['members']:
                project_data[project_key]['members'][member_key] = {
                    'member_id': entry.user_id,
                    'member_name': entry.user_name,
                    'total_duration': 0,
                    'billable_duration': 0,
                    'entry_count': 0,
                    'total_earnings_usd': Decimal('0'),
                    'total_earnings_eur': Decimal('0'),
                    'billable_earnings_usd': Decimal('0'),
                    'billable_earnings_eur': Decimal('0')
                }

            member_data = project_data[project_key]['members'][member_key]
            member_data['total_duration'] += entry.duration
            member_data['entry_count'] += 1
            if entry.billable:
                member_data['billable_duration'] += entry.duration

            # Calculate financial data
            member_db = self.db.query(Member).filter(Member.toggl_id == entry.user_id).first()
            if member_db:
                work_date = entry.start_time.date()
                client_db_id = None
                if client_id:
                    client_db = self.db.query(Client).filter(Client.toggl_id == client_id).first()
                    if client_db:
                        client_db_id = client_db.id

                rate = self.rate_service.get_member_rate(member_db.id, client_db_id, work_date)
                
                if rate:
                    hours = Decimal(entry.duration) / Decimal(3600)
                    
                    if rate.hourly_rate_usd:
                        earnings_usd = hours * rate.hourly_rate_usd
                        member_data['total_earnings_usd'] += earnings_usd
                        project_data[project_key]['total_earnings_usd'] += earnings_usd
                        client_totals['total_earnings_usd'] += earnings_usd
                        
                        if entry.billable:
                            member_data['billable_earnings_usd'] += earnings_usd
                            project_data[project_key]['billable_earnings_usd'] += earnings_usd
                            client_totals['billable_earnings_usd'] += earnings_usd

                    if rate.hourly_rate_eur:
                        earnings_eur = hours * rate.hourly_rate_eur
                        member_data['total_earnings_eur'] += earnings_eur
                        project_data[project_key]['total_earnings_eur'] += earnings_eur
                        client_totals['total_earnings_eur'] += earnings_eur
                        
                        if entry.billable:
                            member_data['billable_earnings_eur'] += earnings_eur
                            project_data[project_key]['billable_earnings_eur'] += earnings_eur
                            client_totals['billable_earnings_eur'] += earnings_eur

        # Format response
        projects = []
        if include_project_breakdown:
            for project_info in project_data.values():
                members = []
                for member_info in project_info['members'].values():
                    members.append({
                        'member_id': member_info['member_id'],
                        'member_name': member_info['member_name'],
                        'total_hours': round(member_info['total_duration'] / 3600, 2),
                        'billable_hours': round(member_info['billable_duration'] / 3600, 2),
                        'entry_count': member_info['entry_count'],
                        'total_earnings_usd': float(member_info['total_earnings_usd']),
                        'total_earnings_eur': float(member_info['total_earnings_eur']),
                        'billable_earnings_usd': float(member_info['billable_earnings_usd']),
                        'billable_earnings_eur': float(member_info['billable_earnings_eur'])
                    })

                # Sort members by total hours
                members.sort(key=lambda m: m['total_hours'], reverse=True)

                projects.append({
                    'project_id': project_info['project_id'],
                    'project_name': project_info['project_name'],
                    'total_hours': round(project_info['total_duration'] / 3600, 2),
                    'billable_hours': round(project_info['billable_duration'] / 3600, 2),
                    'entry_count': project_info['entry_count'],
                    'total_earnings_usd': float(project_info['total_earnings_usd']),
                    'total_earnings_eur': float(project_info['total_earnings_eur']),
                    'billable_earnings_usd': float(project_info['billable_earnings_usd']),
                    'billable_earnings_eur': float(project_info['billable_earnings_eur']),
                    'members': members
                })

        # Sort projects by total hours
        projects.sort(key=lambda p: p['total_hours'], reverse=True)

        return {
            'client_id': client_id,
            'client_name': client_name,
            'workspace_id': workspace_id,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'totals': {
                'total_hours': round(client_totals['total_duration'] / 3600, 2),
                'billable_hours': round(client_totals['billable_duration'] / 3600, 2),
                'entry_count': client_totals['entry_count'],
                'total_earnings_usd': float(client_totals['total_earnings_usd']),
                'total_earnings_eur': float(client_totals['total_earnings_eur']),
                'billable_earnings_usd': float(client_totals['billable_earnings_usd']),
                'billable_earnings_eur': float(client_totals['billable_earnings_eur']),
                'project_count': len(project_data)
            },
            'projects': projects if include_project_breakdown else []
        }

    def get_member_performance_report(
        self,
        workspace_id: int,
        member_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get performance report for a specific member across all clients.
        
        Args:
            workspace_id: Workspace ID
            member_id: Member's Toggl ID
            start_date: Start date for report
            end_date: End date for report
            
        Returns:
            Member performance report with client breakdown
        """
        # Set default date range
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        # Get member info
        member = self.db.query(Member).filter(Member.toggl_id == member_id).first()
        if not member:
            raise ValueError(f"Member with Toggl ID {member_id} not found")

        # Get time entries for this member
        time_entries = self.db.query(TimeEntryCache).filter(
            and_(
                TimeEntryCache.workspace_id == workspace_id,
                TimeEntryCache.user_id == member_id,
                TimeEntryCache.start_time >= datetime.combine(start_date, datetime.min.time()),
                TimeEntryCache.start_time <= datetime.combine(end_date, datetime.max.time()),
                TimeEntryCache.duration > 0
            )
        ).all()

        # Group by client
        client_data = {}
        member_totals = {
            'total_duration': 0,
            'billable_duration': 0,
            'entry_count': 0,
            'total_earnings_usd': Decimal('0'),
            'total_earnings_eur': Decimal('0'),
            'billable_earnings_usd': Decimal('0'),
            'billable_earnings_eur': Decimal('0')
        }

        for entry in time_entries:
            client_key = entry.client_id or 'no_client'
            client_name = entry.client_name or 'No Client'

            if client_key not in client_data:
                client_data[client_key] = {
                    'client_id': entry.client_id,
                    'client_name': client_name,
                    'total_duration': 0,
                    'billable_duration': 0,
                    'entry_count': 0,
                    'total_earnings_usd': Decimal('0'),
                    'total_earnings_eur': Decimal('0'),
                    'billable_earnings_usd': Decimal('0'),
                    'billable_earnings_eur': Decimal('0'),
                    'hourly_rate_usd': None,
                    'hourly_rate_eur': None
                }

            # Add to client totals
            client_data[client_key]['total_duration'] += entry.duration
            client_data[client_key]['entry_count'] += 1
            if entry.billable:
                client_data[client_key]['billable_duration'] += entry.duration

            # Add to member totals
            member_totals['total_duration'] += entry.duration
            member_totals['entry_count'] += 1
            if entry.billable:
                member_totals['billable_duration'] += entry.duration

            # Calculate earnings
            work_date = entry.start_time.date()
            client_db_id = None
            if entry.client_id:
                client_db = self.db.query(Client).filter(Client.toggl_id == entry.client_id).first()
                if client_db:
                    client_db_id = client_db.id

            rate = self.rate_service.get_member_rate(member.id, client_db_id, work_date)
            
            if rate:
                # Store hourly rates
                if client_data[client_key]['hourly_rate_usd'] is None:
                    client_data[client_key]['hourly_rate_usd'] = rate.hourly_rate_usd
                    client_data[client_key]['hourly_rate_eur'] = rate.hourly_rate_eur

                hours = Decimal(entry.duration) / Decimal(3600)
                
                if rate.hourly_rate_usd:
                    earnings_usd = hours * rate.hourly_rate_usd
                    client_data[client_key]['total_earnings_usd'] += earnings_usd
                    member_totals['total_earnings_usd'] += earnings_usd
                    
                    if entry.billable:
                        client_data[client_key]['billable_earnings_usd'] += earnings_usd
                        member_totals['billable_earnings_usd'] += earnings_usd

                if rate.hourly_rate_eur:
                    earnings_eur = hours * rate.hourly_rate_eur
                    client_data[client_key]['total_earnings_eur'] += earnings_eur
                    member_totals['total_earnings_eur'] += earnings_eur
                    
                    if entry.billable:
                        client_data[client_key]['billable_earnings_eur'] += earnings_eur
                        member_totals['billable_earnings_eur'] += earnings_eur

        # Format client breakdown
        clients = []
        for client_info in client_data.values():
            clients.append({
                'client_id': client_info['client_id'],
                'client_name': client_info['client_name'],
                'total_hours': round(client_info['total_duration'] / 3600, 2),
                'billable_hours': round(client_info['billable_duration'] / 3600, 2),
                'entry_count': client_info['entry_count'],
                'total_earnings_usd': float(client_info['total_earnings_usd']),
                'total_earnings_eur': float(client_info['total_earnings_eur']),
                'billable_earnings_usd': float(client_info['billable_earnings_usd']),
                'billable_earnings_eur': float(client_info['billable_earnings_eur']),
                'hourly_rate_usd': float(client_info['hourly_rate_usd']) if client_info['hourly_rate_usd'] else None,
                'hourly_rate_eur': float(client_info['hourly_rate_eur']) if client_info['hourly_rate_eur'] else None
            })

        # Sort clients by total hours
        clients.sort(key=lambda c: c['total_hours'], reverse=True)

        return {
            'member_id': member_id,
            'member_name': member.name,
            'workspace_id': workspace_id,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'totals': {
                'total_hours': round(member_totals['total_duration'] / 3600, 2),
                'billable_hours': round(member_totals['billable_duration'] / 3600, 2),
                'entry_count': member_totals['entry_count'],
                'total_earnings_usd': float(member_totals['total_earnings_usd']),
                'total_earnings_eur': float(member_totals['total_earnings_eur']),
                'billable_earnings_usd': float(member_totals['billable_earnings_usd']),
                'billable_earnings_eur': float(member_totals['billable_earnings_eur']),
                'client_count': len(client_data)
            },
            'clients': clients
        }


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    """
    FastAPI dependency to get ReportService instance.
    
    Args:
        db: Database session from FastAPI dependency
        
    Returns:
        ReportService instance
    """
    return ReportService(db)