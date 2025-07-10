"""
Toggl API Client for retrieving total time tracked for members.

This module provides a comprehensive interface to the Toggl Track API v9 and Reports API v3
to fetch time tracking data for workspace members.
"""

import base64
import logging
import requests
import time
import backoff
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from urllib.parse import urljoin
from dateutil.parser import parse as parse_date


@dataclass
class TimeEntry:
    """Represents a single time entry from Toggl."""
    id: int
    description: str
    duration: int  # Duration in seconds
    start: str
    stop: Optional[str]
    user_id: int
    user_name: str
    project_id: Optional[int]
    project_name: Optional[str]
    workspace_id: int
    billable: bool = False
    tags: Optional[List[str]] = None


@dataclass
class MemberTimeTotal:
    """Represents total time tracked for a member."""
    user_id: int
    user_name: str
    email: Optional[str]
    total_duration_seconds: int
    billable_duration_seconds: int
    entry_count: int
    
    @property
    def total_hours(self) -> float:
        """Get total duration in hours."""
        return self.total_duration_seconds / 3600.0
    
    @property
    def billable_hours(self) -> float:
        """Get billable duration in hours."""
        return self.billable_duration_seconds / 3600.0


class TogglAPIError(Exception):
    """Custom exception for Toggl API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(message)


class TogglRateLimitError(TogglAPIError):
    """Exception for rate limit errors."""
    pass


class TogglAuthenticationError(TogglAPIError):
    """Exception for authentication errors."""
    pass


class TogglPaymentRequiredError(TogglAPIError):
    """Exception for payment required errors."""
    pass


class TogglEndpointGoneError(TogglAPIError):
    """Exception for gone endpoint errors."""
    pass


def _sanitize_credentials(text: str) -> str:
    """Sanitize text to remove potential credential information."""
    if not text:
        return text
    
    # Remove potential API tokens (typically 32-64 character hex strings)
    import re
    sanitized = re.sub(r'[a-fA-F0-9]{32,64}', '[API_TOKEN]', text)
    
    # Remove potential email addresses
    sanitized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', sanitized)
    
    return sanitized


def _validate_date_format(date_str: str) -> bool:
    """Validate date string is in YYYY-MM-DD format."""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def _validate_credentials(api_token: Optional[str] = None, email: Optional[str] = None, 
                         password: Optional[str] = None) -> None:
    """Validate credential parameters."""
    if api_token:
        if not isinstance(api_token, str) or len(api_token) < 10:
            raise TogglAuthenticationError("API token must be a string with at least 10 characters")
    elif email and password:
        if not isinstance(email, str) or '@' not in email:
            raise TogglAuthenticationError("Email must be a valid email address")
        if not isinstance(password, str) or len(password) < 6:
            raise TogglAuthenticationError("Password must be at least 6 characters")
    else:
        raise TogglAuthenticationError("Either api_token or email/password must be provided")


class TogglClient:
    """
    Toggl API client for retrieving time tracking data.
    
    Supports both email/password and API token authentication.
    """
    
    BASE_URL = "https://api.track.toggl.com/api/v9"
    REPORTS_BASE_URL = "https://api.track.toggl.com"
    
    def __init__(self, email: Optional[str] = None, password: Optional[str] = None, 
                 api_token: Optional[str] = None):
        """
        Initialize Toggl client.
        
        Args:
            email: User email for basic auth
            password: User password for basic auth
            api_token: API token for token-based auth
        """
        self.logger = logging.getLogger(__name__)
        
        # Validate credentials
        _validate_credentials(api_token, email, password)
        
        if api_token:
            # Use API token with 'api_token' as password
            self.auth = (api_token, 'api_token')
        elif email and password:
            # Use email/password auth
            self.auth = (email, password)
        else:
            raise TogglAuthenticationError("Either api_token or email/password must be provided")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'TogglTimeTracker/1.0'
        })
        
        # Set up authentication
        self.session.auth = self.auth
        
        # Rate limiting: Track last request time to implement 1 req/sec throttling
        self._last_request_time = 0.0
    
    def _throttle_request(self) -> None:
        """Implement rate limiting to ensure 1 request per second."""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < 1.0:
            sleep_time = 1.0 - time_since_last_request
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    @backoff.on_exception(
        backoff.expo,
        (TogglRateLimitError, requests.exceptions.ConnectionError),
        max_tries=3,
        max_time=300,  # 5 minutes
        base=2
    )
    def _make_request(self, method: str, endpoint: str, base_url: Optional[str] = None, 
                     params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict:
        """
        Make authenticated request to Toggl API with rate limiting and error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            base_url: Base URL to use (defaults to BASE_URL)
            params: Query parameters
            data: Request body data
            
        Returns:
            Dict: Response data
            
        Raises:
            TogglAPIError: If request fails
            TogglRateLimitError: If rate limited
            TogglAuthenticationError: If authentication fails
            TogglPaymentRequiredError: If payment required
            TogglEndpointGoneError: If endpoint is gone
        """
        # Implement rate limiting
        self._throttle_request()
        
        url = urljoin(base_url or self.BASE_URL, endpoint)
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data
            )
            
            # Handle specific HTTP status codes according to Toggl docs
            if response.status_code == 429:
                # Rate limit hit - raise specific exception for retry logic
                error_msg = "Rate limit exceeded. Please retry after a delay."
                self.logger.warning(error_msg)
                raise TogglRateLimitError(error_msg, response.status_code, response.text)
            
            elif response.status_code == 401 or response.status_code == 403:
                # Authentication/authorization failure - don't retry
                sanitized_text = _sanitize_credentials(response.text)
                error_msg = f"Authentication failed (HTTP {response.status_code})"
                self.logger.error(error_msg)
                raise TogglAuthenticationError(error_msg, response.status_code, sanitized_text)
            
            elif response.status_code == 402:
                # Payment required - don't retry
                error_msg = "Payment required. Please upgrade your workspace plan."
                self.logger.error(error_msg)
                raise TogglPaymentRequiredError(error_msg, response.status_code, response.text)
            
            elif response.status_code == 410:
                # Gone - permanently stop using this endpoint
                error_msg = f"Endpoint {endpoint} is no longer available (HTTP 410)"
                self.logger.error(error_msg)
                raise TogglEndpointGoneError(error_msg, response.status_code, response.text)
            
            elif 400 <= response.status_code < 500:
                # Other 4xx errors - don't retry
                sanitized_text = _sanitize_credentials(response.text)
                error_msg = f"Client error (HTTP {response.status_code})"
                self.logger.error(f"API request failed: {error_msg}")
                raise TogglAPIError(error_msg, response.status_code, sanitized_text)
            
            elif response.status_code >= 500:
                # 5xx errors - will be retried by backoff decorator
                sanitized_text = _sanitize_credentials(response.text)
                error_msg = f"Server error (HTTP {response.status_code})"
                self.logger.warning(f"Server error, will retry: {error_msg}")
                raise TogglAPIError(error_msg, response.status_code, sanitized_text)
            
            # Success - handle response
            response.raise_for_status()
            
            # Handle empty responses
            if not response.content:
                return {}
                
            return response.json()
            
        except (TogglRateLimitError, TogglAuthenticationError, TogglPaymentRequiredError, 
                TogglEndpointGoneError):
            # Re-raise our custom exceptions
            raise
        except requests.exceptions.HTTPError as e:
            # This shouldn't happen due to our status code handling above
            sanitized_text = _sanitize_credentials(str(e))
            error_msg = f"HTTP error: {sanitized_text}"
            self.logger.error(error_msg)
            raise TogglAPIError(error_msg) from e
        except requests.exceptions.RequestException as e:
            # Network errors - can be retried
            sanitized_text = _sanitize_credentials(str(e))
            error_msg = f"Request failed: {sanitized_text}"
            self.logger.error(error_msg)
            raise TogglAPIError(error_msg) from e
        except ValueError as e:
            # JSON parsing error - likely not retryable
            error_msg = f"Invalid JSON response: {str(e)}"
            self.logger.error(error_msg)
            raise TogglAPIError(error_msg) from e
    
    def get_current_user(self) -> Dict:
        """Get current user information."""
        return self._make_request('GET', '/me')
    
    def get_workspaces(self) -> List[Dict]:
        """Get list of workspaces accessible to the user."""
        return self._make_request('GET', '/workspaces')
    
    def get_workspace_users(self, workspace_id: int) -> List[Dict]:
        """Get users in a specific workspace."""
        return self._make_request('GET', f'/workspaces/{workspace_id}/users')
    
    def get_time_entries(self, start_date: Optional[str] = None, 
                        end_date: Optional[str] = None,
                        user_id: Optional[int] = None) -> List[TimeEntry]:
        """
        Get time entries for the authenticated user.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            user_id: Specific user ID (requires workspace admin access)
            
        Returns:
            List[TimeEntry]: List of time entries
        """
        # Validate date formats
        if start_date and not _validate_date_format(start_date):
            raise TogglAPIError(f"Invalid start_date format: {start_date}. Use YYYY-MM-DD format.")
        if end_date and not _validate_date_format(end_date):
            raise TogglAPIError(f"Invalid end_date format: {end_date}. Use YYYY-MM-DD format.")
        
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        
        response = self._make_request('GET', '/me/time_entries', params=params)
        
        # Handle both array and object responses
        if isinstance(response, list):
            entries_data = response
        else:
            entries_data = response.get('data', response.get('items', []))
        
        entries = []
        for entry_data in entries_data:
            entries.append(TimeEntry(
                id=entry_data['id'],
                description=entry_data.get('description', ''),
                duration=entry_data['duration'],
                start=entry_data['start'],
                stop=entry_data.get('stop'),
                user_id=entry_data['user_id'],
                user_name=entry_data.get('user_name', ''),
                project_id=entry_data.get('project_id'),
                project_name=entry_data.get('project_name', ''),
                workspace_id=entry_data['workspace_id'],
                billable=entry_data.get('billable', False),
                tags=entry_data.get('tags', [])
            ))
        
        return entries
    
    def get_workspace_time_entries(self, workspace_id: int, start_date: Optional[str] = None,
                                  end_date: Optional[str] = None) -> List[TimeEntry]:
        """
        Get time entries for all users in a workspace using Reports API.
        
        Args:
            workspace_id: Workspace ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List[TimeEntry]: List of time entries for all workspace users
        """
        # Validate date formats
        if start_date and not _validate_date_format(start_date):
            raise TogglAPIError(f"Invalid start_date format: {start_date}. Use YYYY-MM-DD format.")
        if end_date and not _validate_date_format(end_date):
            raise TogglAPIError(f"Invalid end_date format: {end_date}. Use YYYY-MM-DD format.")
        
        # Use Reports API for workspace-wide data
        endpoint = f'/reports/api/v3/workspace/{workspace_id}/search/time_entries'
        
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        
        # Add pagination support
        params['first_row_number'] = 1
        params['max_rows'] = 1000  # Adjust as needed
        
        try:
            response = self._make_request(
                'POST', endpoint, 
                base_url=self.REPORTS_BASE_URL,
                data=params
            )
            
            entries = []
            time_entries = response.get('data', [])
            
            for entry_data in time_entries:
                entries.append(TimeEntry(
                    id=entry_data.get('id', 0),
                    description=entry_data.get('description', ''),
                    duration=entry_data.get('dur', 0) // 1000,  # Convert from milliseconds
                    start=entry_data.get('start', ''),
                    stop=entry_data.get('end', ''),
                    user_id=entry_data.get('uid', 0),
                    user_name=entry_data.get('user', ''),
                    project_id=entry_data.get('pid'),
                    project_name=entry_data.get('project', ''),
                    workspace_id=workspace_id,
                    billable=entry_data.get('is_billable', False),
                    tags=entry_data.get('tags', [])
                ))
            
            return entries
            
        except TogglAPIError:
            # Fallback to individual user time entries if Reports API fails
            self.logger.warning("Reports API failed, falling back to individual user queries")
            return self._get_time_entries_fallback(workspace_id, start_date, end_date)
    
    def _get_time_entries_fallback(self, workspace_id: int, start_date: Optional[str], 
                                  end_date: Optional[str]) -> List[TimeEntry]:
        """Fallback method to get time entries for all workspace users."""
        all_entries = []
        
        # Get workspace users
        users = self.get_workspace_users(workspace_id)
        
        for user in users:
            try:
                # Note: This might require workspace admin permissions
                user_entries = self.get_time_entries(start_date, end_date, user['id'])
                all_entries.extend(user_entries)
            except TogglAPIError as e:
                self.logger.warning(f"Failed to get entries for user {user.get('name', user['id'])}: {e}")
                continue
        
        return all_entries
    
    def get_member_total_time(self, workspace_id: int, user_id: Optional[int] = None,
                            start_date: Optional[str] = None, end_date: Optional[str] = None) -> Union[MemberTimeTotal, List[MemberTimeTotal]]:
        """
        Get total time tracked for a member or all members in workspace.
        
        Args:
            workspace_id: Workspace ID
            user_id: Specific user ID (if None, returns all users)
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            MemberTimeTotal or List[MemberTimeTotal]: Time totals for member(s)
        """
        # Validate date formats
        if start_date and not _validate_date_format(start_date):
            raise TogglAPIError(f"Invalid start_date format: {start_date}. Use YYYY-MM-DD format.")
        if end_date and not _validate_date_format(end_date):
            raise TogglAPIError(f"Invalid end_date format: {end_date}. Use YYYY-MM-DD format.")
        
        # Get time entries
        if user_id:
            # Get entries for specific user
            entries = self.get_time_entries(start_date, end_date, user_id)
        else:
            # Get entries for all workspace users
            entries = self.get_workspace_time_entries(workspace_id, start_date, end_date)
        
        # Aggregate by user
        user_totals = {}
        
        for entry in entries:
            uid = entry.user_id
            
            if uid not in user_totals:
                user_totals[uid] = {
                    'user_id': uid,
                    'user_name': entry.user_name,
                    'total_duration': 0,
                    'billable_duration': 0,
                    'entry_count': 0
                }
            
            # Only count positive durations (negative means running)
            if entry.duration > 0:
                user_totals[uid]['total_duration'] += entry.duration
                if entry.billable:
                    user_totals[uid]['billable_duration'] += entry.duration
                user_totals[uid]['entry_count'] += 1
        
        # Convert to MemberTimeTotal objects
        results = []
        for user_data in user_totals.values():
            results.append(MemberTimeTotal(
                user_id=user_data['user_id'],
                user_name=user_data['user_name'],
                email=None,  # Would need additional API call to get email
                total_duration_seconds=user_data['total_duration'],
                billable_duration_seconds=user_data['billable_duration'],
                entry_count=user_data['entry_count']
            ))
        
        if user_id:
            # Return single result for specific user
            user_result = next((r for r in results if r.user_id == user_id), None)
            if not user_result:
                return MemberTimeTotal(
                    user_id=user_id,
                    user_name='Unknown',
                    email=None,
                    total_duration_seconds=0,
                    billable_duration_seconds=0,
                    entry_count=0
                )
            return user_result
        else:
            # Return all users
            return results
    
    def get_summary_report(self, workspace_id: int, start_date: str, end_date: str,
                          user_ids: Optional[List[int]] = None) -> Dict:
        """
        Get summary report for workspace using Reports API.
        
        Args:
            workspace_id: Workspace ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            user_ids: List of specific user IDs (optional)
            
        Returns:
            Dict: Summary report data
        """
        # Validate date formats
        if not _validate_date_format(start_date):
            raise TogglAPIError(f"Invalid start_date format: {start_date}. Use YYYY-MM-DD format.")
        if not _validate_date_format(end_date):
            raise TogglAPIError(f"Invalid end_date format: {end_date}. Use YYYY-MM-DD format.")
        
        endpoint = f'/reports/api/v3/workspace/{workspace_id}/summary/time_entries'
        
        data = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        if user_ids:
            data['user_ids'] = user_ids
        
        return self._make_request(
            'POST', endpoint,
            base_url=self.REPORTS_BASE_URL,
            data=data
        ) 