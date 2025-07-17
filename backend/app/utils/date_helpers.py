"""
Date utility functions for report filtering and date range calculations.
"""

from datetime import date, datetime, timedelta
from typing import Tuple, Optional, List
from calendar import monthrange
import calendar

from app.schemas.reports import ReportPeriod


def get_date_range_for_period(period: ReportPeriod, custom_start: Optional[date] = None, 
                            custom_end: Optional[date] = None) -> Tuple[date, date]:
    """
    Calculate start and end dates for predefined report periods.
    
    Args:
        period: Report period enum
        custom_start: Custom start date (for CUSTOM period)
        custom_end: Custom end date (for CUSTOM period)
        
    Returns:
        Tuple of (start_date, end_date)
        
    Raises:
        ValueError: If custom period is selected but dates are not provided
    """
    today = date.today()
    
    if period == ReportPeriod.LAST_7_DAYS:
        start_date = today - timedelta(days=7)
        end_date = today
        
    elif period == ReportPeriod.LAST_30_DAYS:
        start_date = today - timedelta(days=30)
        end_date = today
        
    elif period == ReportPeriod.LAST_90_DAYS:
        start_date = today - timedelta(days=90)
        end_date = today
        
    elif period == ReportPeriod.THIS_MONTH:
        start_date = today.replace(day=1)
        end_date = today
        
    elif period == ReportPeriod.LAST_MONTH:
        # Get first day of last month
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        start_date = last_day_last_month.replace(day=1)
        end_date = last_day_last_month
        
    elif period == ReportPeriod.THIS_QUARTER:
        start_date, end_date = get_current_quarter_dates(today)
        end_date = min(end_date, today)  # Don't go beyond today
        
    elif period == ReportPeriod.LAST_QUARTER:
        start_date, end_date = get_last_quarter_dates(today)
        
    elif period == ReportPeriod.THIS_YEAR:
        start_date = today.replace(month=1, day=1)
        end_date = today
        
    elif period == ReportPeriod.CUSTOM:
        if not custom_start or not custom_end:
            raise ValueError("Custom start and end dates are required for CUSTOM period")
        start_date = custom_start
        end_date = custom_end
        
    else:
        raise ValueError(f"Unknown report period: {period}")
    
    # Validate date range
    if start_date > end_date:
        raise ValueError("Start date cannot be after end date")
    
    if end_date > today:
        raise ValueError("End date cannot be in the future")
    
    return start_date, end_date


def get_current_quarter_dates(reference_date: date) -> Tuple[date, date]:
    """
    Get start and end dates for the current quarter based on a reference date.
    
    Args:
        reference_date: Reference date to determine the quarter
        
    Returns:
        Tuple of (start_date, end_date) for the quarter
    """
    year = reference_date.year
    month = reference_date.month
    
    # Determine quarter
    if month <= 3:  # Q1
        start_date = date(year, 1, 1)
        end_date = date(year, 3, 31)
    elif month <= 6:  # Q2
        start_date = date(year, 4, 1)
        end_date = date(year, 6, 30)
    elif month <= 9:  # Q3
        start_date = date(year, 7, 1)
        end_date = date(year, 9, 30)
    else:  # Q4
        start_date = date(year, 10, 1)
        end_date = date(year, 12, 31)
    
    return start_date, end_date


def get_last_quarter_dates(reference_date: date) -> Tuple[date, date]:
    """
    Get start and end dates for the quarter before the current quarter.
    
    Args:
        reference_date: Reference date to determine the current quarter
        
    Returns:
        Tuple of (start_date, end_date) for the last quarter
    """
    year = reference_date.year
    month = reference_date.month
    
    # Determine current quarter and calculate last quarter
    if month <= 3:  # Currently Q1, last quarter is Q4 of previous year
        start_date = date(year - 1, 10, 1)
        end_date = date(year - 1, 12, 31)
    elif month <= 6:  # Currently Q2, last quarter is Q1
        start_date = date(year, 1, 1)
        end_date = date(year, 3, 31)
    elif month <= 9:  # Currently Q3, last quarter is Q2
        start_date = date(year, 4, 1)
        end_date = date(year, 6, 30)
    else:  # Currently Q4, last quarter is Q3
        start_date = date(year, 7, 1)
        end_date = date(year, 9, 30)
    
    return start_date, end_date


def get_month_range(year: int, month: int) -> Tuple[date, date]:
    """
    Get start and end dates for a specific month.
    
    Args:
        year: Year
        month: Month (1-12)
        
    Returns:
        Tuple of (start_date, end_date) for the month
    """
    start_date = date(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date(year, month, last_day)
    
    return start_date, end_date


def get_week_range(reference_date: date, week_start_day: int = 0) -> Tuple[date, date]:
    """
    Get start and end dates for the week containing the reference date.
    
    Args:
        reference_date: Reference date within the week
        week_start_day: Day of week that starts the week (0=Monday, 6=Sunday)
        
    Returns:
        Tuple of (start_date, end_date) for the week
    """
    days_since_week_start = (reference_date.weekday() - week_start_day) % 7
    start_date = reference_date - timedelta(days=days_since_week_start)
    end_date = start_date + timedelta(days=6)
    
    return start_date, end_date


def format_date_range_description(start_date: date, end_date: date, period: Optional[ReportPeriod] = None) -> str:
    """
    Create a human-readable description of a date range.
    
    Args:
        start_date: Start date
        end_date: End date
        period: Optional original period enum for accurate labeling
        
    Returns:
        Human-readable date range description
    """
    today = date.today()
    
    # If we have the original period, use it for primary determination
    if period:
        if period == ReportPeriod.LAST_7_DAYS:
            return "Last 7 days"
        elif period == ReportPeriod.LAST_30_DAYS:
            return "Last 30 days"
        elif period == ReportPeriod.LAST_90_DAYS:
            return "Last 90 days"
        elif period == ReportPeriod.THIS_MONTH:
            if end_date == today:
                return f"This month (through {end_date.strftime('%B %d')})"
            else:
                return "This month"
        elif period == ReportPeriod.LAST_MONTH:
            return "Last month"
        elif period == ReportPeriod.THIS_QUARTER:
            if end_date == today:
                return f"This quarter (through {end_date.strftime('%B %d')})"
            else:
                return "This quarter"
        elif period == ReportPeriod.LAST_QUARTER:
            return "Last quarter"
        elif period == ReportPeriod.THIS_YEAR:
            if end_date == today:
                return f"This year (through {end_date.strftime('%B %d')})"
            else:
                return "This year"
        elif period == ReportPeriod.CUSTOM:
            # Fall through to date-based logic for custom ranges
            pass
    
    # Special cases for common ranges
    if start_date == end_date:
        if start_date == today:
            return "Today"
        elif start_date == today - timedelta(days=1):
            return "Yesterday"
        else:
            return start_date.strftime("%B %d, %Y")
    
    # Check for common periods
    if end_date == today:
        days_diff = (today - start_date).days
        if days_diff == 7:
            return "Last 7 days"
        elif days_diff == 30:
            return "Last 30 days"
        elif days_diff == 90:
            return "Last 90 days"
    
    # Check for month ranges
    if (start_date.day == 1 and 
        end_date == date(end_date.year, end_date.month, 
                        monthrange(end_date.year, end_date.month)[1])):
        if start_date.year == end_date.year and start_date.month == end_date.month:
            if start_date.year == today.year and start_date.month == today.month:
                return "This month"
            elif (start_date.year == today.year and 
                  start_date.month == today.month - 1) or \
                 (today.month == 1 and start_date.year == today.year - 1 and 
                  start_date.month == 12):
                return "Last month"
            else:
                return start_date.strftime("%B %Y")
    
    # Check for quarter ranges
    current_quarter_start, current_quarter_end = get_current_quarter_dates(today)
    last_quarter_start, last_quarter_end = get_last_quarter_dates(today)
    
    if start_date == current_quarter_start and end_date >= current_quarter_start:
        if end_date >= current_quarter_end:
            return "This quarter"
        else:
            return f"This quarter (through {end_date.strftime('%B %d')})"
    elif start_date == last_quarter_start and end_date == last_quarter_end:
        return "Last quarter"
    
    # Check for year ranges
    if (start_date.month == 1 and start_date.day == 1 and
        end_date.month == 12 and end_date.day == 31 and
        start_date.year == end_date.year):
        if start_date.year == today.year:
            return "This year"
        else:
            return str(start_date.year)
    
    # Default format
    if start_date.year == end_date.year:
        if start_date.month == end_date.month:
            return f"{start_date.strftime('%B %d')} - {end_date.strftime('%d, %Y')}"
        else:
            return f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
    else:
        return f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"


def get_business_days_count(start_date: date, end_date: date, 
                           exclude_weekends: bool = True) -> int:
    """
    Calculate the number of business days in a date range.
    
    Args:
        start_date: Start date
        end_date: End date
        exclude_weekends: Whether to exclude weekends
        
    Returns:
        Number of business days
    """
    if start_date > end_date:
        return 0
    
    total_days = (end_date - start_date).days + 1
    
    if not exclude_weekends:
        return total_days
    
    # Count business days
    business_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Monday = 0, Sunday = 6
        if current_date.weekday() < 5:  # Monday to Friday
            business_days += 1
        current_date += timedelta(days=1)
    
    return business_days


def split_date_range_by_month(start_date: date, end_date: date) -> List[Tuple[date, date]]:
    """
    Split a date range into monthly chunks.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        List of (start_date, end_date) tuples for each month
    """
    if start_date > end_date:
        return []
    
    chunks = []
    current_date = start_date
    
    while current_date <= end_date:
        # Get end of current month
        _, last_day = monthrange(current_date.year, current_date.month)
        month_end = date(current_date.year, current_date.month, last_day)
        
        # Use the earlier of month end or overall end date
        chunk_end = min(month_end, end_date)
        
        chunks.append((current_date, chunk_end))
        
        # Move to first day of next month
        if chunk_end < end_date:
            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, 1)
            else:
                current_date = date(current_date.year, current_date.month + 1, 1)
        else:
            break
    
    return chunks


def is_same_period(date1: date, date2: date, period_type: str) -> bool:
    """
    Check if two dates fall within the same period.
    
    Args:
        date1: First date
        date2: Second date
        period_type: Type of period ('day', 'week', 'month', 'quarter', 'year')
        
    Returns:
        True if dates are in the same period
    """
    if period_type == 'day':
        return date1 == date2
    
    elif period_type == 'week':
        # Check if both dates are in the same week (Monday to Sunday)
        week1_start, week1_end = get_week_range(date1)
        return week1_start <= date2 <= week1_end
    
    elif period_type == 'month':
        return date1.year == date2.year and date1.month == date2.month
    
    elif period_type == 'quarter':
        quarter1_start, quarter1_end = get_current_quarter_dates(date1)
        return quarter1_start <= date2 <= quarter1_end
    
    elif period_type == 'year':
        return date1.year == date2.year
    
    else:
        raise ValueError(f"Unknown period type: {period_type}")


def validate_date_range(start_date: Optional[date], end_date: Optional[date], 
                       max_days: Optional[int] = None) -> Tuple[date, date]:
    """
    Validate and normalize a date range.
    
    Args:
        start_date: Start date (defaults to 30 days ago)
        end_date: End date (defaults to today)
        max_days: Maximum allowed range in days
        
    Returns:
        Validated (start_date, end_date) tuple
        
    Raises:
        ValueError: If date range is invalid
    """
    today = date.today()
    
    # Set defaults
    if end_date is None:
        end_date = today
    if start_date is None:
        start_date = end_date - timedelta(days=30)
    
    # Validate basic constraints
    if start_date > end_date:
        raise ValueError("Start date cannot be after end date")
    
    if end_date > today:
        raise ValueError("End date cannot be in the future")
    
    # Check maximum range if specified
    if max_days:
        range_days = (end_date - start_date).days
        if range_days > max_days:
            raise ValueError(f"Date range cannot exceed {max_days} days")
    
    return start_date, end_date