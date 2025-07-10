"""
Pydantic schemas for report API requests and responses.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class ReportPeriod(str, Enum):
    """Predefined report periods."""
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_QUARTER = "this_quarter"
    LAST_QUARTER = "last_quarter"
    THIS_YEAR = "this_year"
    CUSTOM = "custom"


class ReportCurrency(str, Enum):
    """Supported currencies for financial reports."""
    USD = "usd"
    EUR = "eur"
    BOTH = "both"


class ReportRequest(BaseModel):
    """Base request schema for reports."""
    workspace_id: int
    period: Optional[ReportPeriod] = ReportPeriod.LAST_30_DAYS
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    client_ids: Optional[List[int]] = None
    member_ids: Optional[List[int]] = None
    include_non_billable: bool = True
    include_financial: bool = True
    currency: ReportCurrency = ReportCurrency.BOTH

    @validator('end_date')
    def end_date_not_in_future(cls, v):
        if v and v > date.today():
            raise ValueError('End date cannot be in the future')
        return v

    @validator('start_date')
    def start_date_before_end_date(cls, v, values):
        if v and 'end_date' in values and values['end_date']:
            if v > values['end_date']:
                raise ValueError('Start date must be before end date')
        return v


class ClientReportRequest(ReportRequest):
    """Request schema for client reports."""
    include_project_breakdown: bool = True
    sort_by: str = Field(default="total_hours", regex="^(total_hours|billable_hours|total_earnings_usd|total_earnings_eur|client_name)$")
    sort_order: str = Field(default="desc", regex="^(asc|desc)$")


class MemberReportRequest(ReportRequest):
    """Request schema for member reports."""
    member_id: int
    include_client_breakdown: bool = True
    include_project_breakdown: bool = False


class MemberReportData(BaseModel):
    """Member data within a report."""
    member_id: int
    member_name: str
    total_hours: float = Field(..., ge=0)
    billable_hours: float = Field(..., ge=0)
    entry_count: int = Field(..., ge=0)
    total_earnings_usd: Optional[float] = Field(None, ge=0)
    total_earnings_eur: Optional[float] = Field(None, ge=0)
    billable_earnings_usd: Optional[float] = Field(None, ge=0)
    billable_earnings_eur: Optional[float] = Field(None, ge=0)
    hourly_rate_usd: Optional[float] = Field(None, ge=0)
    hourly_rate_eur: Optional[float] = Field(None, ge=0)

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v else None
        }


class ProjectReportData(BaseModel):
    """Project data within a client report."""
    project_id: Optional[int]
    project_name: str
    total_hours: float = Field(..., ge=0)
    billable_hours: float = Field(..., ge=0)
    entry_count: int = Field(..., ge=0)
    total_earnings_usd: Optional[float] = Field(None, ge=0)
    total_earnings_eur: Optional[float] = Field(None, ge=0)
    billable_earnings_usd: Optional[float] = Field(None, ge=0)
    billable_earnings_eur: Optional[float] = Field(None, ge=0)
    members: List[MemberReportData] = []

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v else None
        }


class ClientReportData(BaseModel):
    """Client data in reports."""
    client_id: Optional[int]
    client_name: str
    total_hours: float = Field(..., ge=0)
    billable_hours: float = Field(..., ge=0)
    total_earnings_usd: Optional[float] = Field(None, ge=0)
    total_earnings_eur: Optional[float] = Field(None, ge=0)
    billable_earnings_usd: Optional[float] = Field(None, ge=0)
    billable_earnings_eur: Optional[float] = Field(None, ge=0)
    project_count: int = Field(..., ge=0)
    member_reports: List[MemberReportData] = []
    
    @property
    def billable_percentage(self) -> float:
        """Calculate billable percentage."""
        if self.total_hours > 0:
            return round((self.billable_hours / self.total_hours) * 100, 1)
        return 0.0

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v else None
        }


class ReportTotals(BaseModel):
    """Report totals summary."""
    total_hours: float = Field(..., ge=0)
    billable_hours: float = Field(..., ge=0)
    entry_count: int = Field(..., ge=0)
    total_earnings_usd: Optional[float] = Field(None, ge=0)
    total_earnings_eur: Optional[float] = Field(None, ge=0)
    billable_earnings_usd: Optional[float] = Field(None, ge=0)
    billable_earnings_eur: Optional[float] = Field(None, ge=0)
    
    @property
    def billable_percentage(self) -> float:
        """Calculate billable percentage."""
        if self.total_hours > 0:
            return round((self.billable_hours / self.total_hours) * 100, 1)
        return 0.0

    @property
    def average_hourly_rate_usd(self) -> Optional[float]:
        """Calculate average hourly rate in USD."""
        if self.total_hours > 0 and self.total_earnings_usd:
            return round(self.total_earnings_usd / self.total_hours, 2)
        return None

    @property
    def average_hourly_rate_eur(self) -> Optional[float]:
        """Calculate average hourly rate in EUR."""
        if self.total_hours > 0 and self.total_earnings_eur:
            return round(self.total_earnings_eur / self.total_hours, 2)
        return None

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v else None
        }


class WorkspaceReportResponse(BaseModel):
    """Response schema for workspace reports."""
    workspace_id: int
    date_range: Dict[str, str]  # start and end dates
    totals: ReportTotals
    summary: Dict[str, int]  # total_clients, total_members, total_projects
    client_reports: List[ClientReportData]
    generated_at: datetime
    report_type: str = "workspace_summary"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v) if v else None
        }


class ClientDetailResponse(BaseModel):
    """Response schema for detailed client reports."""
    client_id: Optional[int]
    client_name: str
    workspace_id: int
    date_range: Dict[str, str]
    totals: ReportTotals
    projects: List[ProjectReportData] = []
    generated_at: datetime
    report_type: str = "client_detail"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v) if v else None
        }


class MemberPerformanceResponse(BaseModel):
    """Response schema for member performance reports."""
    member_id: int
    member_name: str
    workspace_id: int
    date_range: Dict[str, str]
    totals: ReportTotals
    clients: List[Dict[str, Any]] = []  # Client breakdown with earnings and rates
    generated_at: datetime
    report_type: str = "member_performance"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v) if v else None
        }


class ReportExportRequest(BaseModel):
    """Request schema for report exports."""
    report_type: str = Field(..., regex="^(workspace|client_detail|member_performance)$")
    format: str = Field(default="json", regex="^(json|csv|pdf)$")
    workspace_id: int
    client_id: Optional[int] = None
    member_id: Optional[int] = None
    period: Optional[ReportPeriod] = ReportPeriod.LAST_30_DAYS
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    include_financial: bool = True
    currency: ReportCurrency = ReportCurrency.BOTH


class TimeEntryDetail(BaseModel):
    """Detailed time entry for drill-down reports."""
    id: int
    description: str
    duration_hours: float
    start_time: datetime
    stop_time: Optional[datetime]
    user_name: str
    project_name: Optional[str]
    client_name: Optional[str]
    billable: bool
    tags: List[str] = []
    earnings_usd: Optional[float] = None
    earnings_eur: Optional[float] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v) if v else None
        }


class DrillDownRequest(BaseModel):
    """Request schema for drill-down reports."""
    workspace_id: int
    client_id: Optional[int] = None
    member_id: Optional[int] = None
    project_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    billable_only: bool = False
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    sort_by: str = Field(default="start_time", regex="^(start_time|duration|description|user_name|project_name|client_name)$")
    sort_order: str = Field(default="desc", regex="^(asc|desc)$")


class DrillDownResponse(BaseModel):
    """Response schema for drill-down reports."""
    workspace_id: int
    filters: Dict[str, Any]
    total_entries: int
    entries: List[TimeEntryDetail]
    pagination: Dict[str, int]  # limit, offset, total_pages
    summary: ReportTotals
    generated_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v) if v else None
        }