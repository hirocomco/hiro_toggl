"""
Toggl API Integration Package

This package provides a comprehensive interface to the Toggl Track API for
retrieving time tracking data and member statistics.
"""

from .toggl_client import (
    TogglClient,
    TogglAPIError,
    TimeEntry,
    MemberTimeTotal
)

__version__ = "1.0.0"
__author__ = "Toggl API Integration"

__all__ = [
    "TogglClient",
    "TogglAPIError", 
    "TimeEntry",
    "MemberTimeTotal"
] 