"""
Enhanced Toggl API Client with client support for generating client-based reports.

This module extends the original Toggl client with client-project relationship mapping
and additional data models for comprehensive reporting.
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
class Client:
    """Represents a Toggl client."""
    id: int
    name: str
    workspace_id: int
    notes: Optional[str] = None
    external_reference: Optional[str] = None
    archived: bool = False


@dataclass
class Project:
    """Represents a Toggl project."""
    id: int
    name: str
    workspace_id: int
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    billable: bool = False
    is_private: bool = False
    active: bool = True
    color: Optional[str] = None


@dataclass
class TimeEntry:
    """Represents a single time entry from Toggl."""
    id: int
    description: str
    duration: int  # Duration in seconds
    start: str
    user_id: int
    user_name: str
    workspace_id: int
    stop: Optional[str] = None
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    billable: bool = False
    tags: Optional[List[str]] = None
    client_id: Optional[int] = None
    client_name: Optional[str] = None


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


@dataclass
class ClientReport:
    """Represents a client report with member breakdown."""
    client_id: Optional[int]
    client_name: str
    total_duration_seconds: int
    billable_duration_seconds: int
    member_reports: List['MemberClientReport']
    
    @property
    def total_hours(self) -> float:
        """Get total duration in hours."""
        return self.total_duration_seconds / 3600.0
    
    @property
    def billable_hours(self) -> float:
        """Get billable duration in hours."""
        return self.billable_duration_seconds / 3600.0


@dataclass
class MemberClientReport:
    """Represents a member's time for a specific client."""
    user_id: int
    user_name: str
    client_id: Optional[int]
    client_name: str
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


class EnhancedTogglClient:
    """
    Enhanced Toggl API client with client support for generating client-based reports.
    
    Extends the original client with client-project relationship mapping.
    """
    
    BASE_URL = "https://api.track.toggl.com/api/v9"
    REPORTS_BASE_URL = "https://api.track.toggl.com"
    
    def __init__(self, email: Optional[str] = None, password: Optional[str] = None, 
                 api_token: Optional[str] = None):
        """
        Initialize Enhanced Toggl client.
        
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
        
        # Cache for client-project mappings
        self._client_project_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes
    
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
        """
        # Implement rate limiting
        self._throttle_request()
        
        base = base_url or self.BASE_URL
        # Ensure base URL ends with / and endpoint doesn't start with / for proper joining
        if not base.endswith('/'):
            base += '/'
        endpoint = endpoint.lstrip('/')
        url = urljoin(base, endpoint)
        
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
    
    def get_workspace_clients(self, workspace_id: int) -> List[Client]:
        """Get all clients in a workspace."""
        response = self._make_request('GET', f'/workspaces/{workspace_id}/clients')
        
        clients = []
        for client_data in response:
            clients.append(Client(
                id=client_data['id'],
                name=client_data['name'],
                notes=client_data.get('notes'),
                external_reference=client_data.get('external_reference'),
                archived=client_data.get('archived', False),
                workspace_id=workspace_id
            ))
        
        return clients
    
    def get_workspace_projects(self, workspace_id: int) -> List[Project]:
        """Get all projects in a workspace with client information."""
        response = self._make_request('GET', f'/workspaces/{workspace_id}/projects')
        
        projects = []
        for project_data in response:
            projects.append(Project(
                id=project_data['id'],
                name=project_data['name'],
                client_id=project_data.get('client_id'),
                workspace_id=workspace_id,
                billable=project_data.get('billable', False),
                is_private=project_data.get('is_private', False),
                active=project_data.get('active', True),
                color=project_data.get('color')
            ))
        
        return projects
    
    def _build_client_project_mapping(self, workspace_id: int) -> Dict[int, Dict]:
        """Build mapping from project_id to client info with caching."""
        current_time = time.time()
        
        # Check cache validity
        cache_key = f"workspace_{workspace_id}"
        if (cache_key in self._client_project_cache and 
            current_time - self._cache_timestamp < self._cache_ttl):
            return self._client_project_cache[cache_key]
        
        # Fetch fresh data
        projects = self.get_workspace_projects(workspace_id)
        clients = self.get_workspace_clients(workspace_id)
        
        # Create client lookup
        client_lookup = {client.id: client for client in clients}
        
        # Create project to client mapping
        project_client_mapping = {}
        for project in projects:
            client_id = project.client_id
            if client_id and client_id in client_lookup:
                client = client_lookup[client_id]
                project_client_mapping[project.id] = {
                    'client_id': client.id,
                    'client_name': client.name
                }
            else:
                project_client_mapping[project.id] = {
                    'client_id': None,
                    'client_name': 'No Client'
                }
        
        # Cache the result
        self._client_project_cache[cache_key] = project_client_mapping
        self._cache_timestamp = current_time
        
        return project_client_mapping
    
    def get_workspace_time_entries_with_clients(self, workspace_id: int, 
                                               start_date: Optional[str] = None,
                                               end_date: Optional[str] = None) -> List[TimeEntry]:
        """
        Get time entries for all users in a workspace with client information.
        
        Args:
            workspace_id: Workspace ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List[TimeEntry]: List of time entries with client information
        """
        # Validate date formats
        if start_date and not _validate_date_format(start_date):
            raise TogglAPIError(f"Invalid start_date format: {start_date}. Use YYYY-MM-DD format.")
        if end_date and not _validate_date_format(end_date):
            raise TogglAPIError(f"Invalid end_date format: {end_date}. Use YYYY-MM-DD format.")
        
        # Build client-project mapping
        client_mapping = self._build_client_project_mapping(workspace_id)
        
        # Get time entries using Reports API
        endpoint = f'/reports/api/v3/workspace/{workspace_id}/search/time_entries'
        
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        
        # Implement pagination to get all entries (API returns max 50 per request)
        entries = []
        page = 1
        page_size = 50
        
        try:
            while True:
                # Set pagination parameters
                params['first_row_number'] = ((page - 1) * page_size) + 1
                params['max_rows'] = page_size
                
                response = self._make_request(
                    'POST', endpoint, 
                    base_url=self.REPORTS_BASE_URL,
                    data=params
                )
                
                # Handle both dict response with 'data' key and direct list response
                if isinstance(response, dict):
                    time_entries = response.get('data', [])
                else:
                    time_entries = response
                
                # Process entries from this page
                for entry_data in time_entries:
                    project_id = entry_data.get('project_id')
                    
                    # Get client info from mapping
                    client_info = client_mapping.get(project_id, {
                        'client_id': None,
                        'client_name': 'No Client'
                    })
                    
                    # Handle nested time_entries structure from Reports API
                    for time_entry in entry_data.get('time_entries', []):
                        entries.append(TimeEntry(
                            id=time_entry.get('id', 0),
                            description=entry_data.get('description', ''),
                            duration=time_entry.get('seconds', 0),  # Reports API uses 'seconds'
                            start=time_entry.get('start', ''),
                            stop=time_entry.get('stop', ''),
                            user_id=entry_data.get('user_id', 0),
                            user_name=entry_data.get('username', ''),
                            project_id=entry_data.get('project_id'),  # Use actual Toggl project ID
                            project_name='',  # Project name not directly available in this format
                            workspace_id=workspace_id,
                            billable=entry_data.get('billable', False),
                            tags=entry_data.get('tag_ids', []),
                            client_id=client_info['client_id'],
                            client_name=client_info['client_name']
                        ))
                
                # If we got less than page_size entries, we're done
                if len(time_entries) < page_size:
                    break
                
                page += 1
                
                # Safety check to prevent infinite loops
                if page > 100:  # Max 5000 entries (100 pages * 50)
                    self.logger.warning(f"Reached maximum page limit (100) for time entries")
                    break
            
            return entries
            
        except TogglAPIError:
            # Fallback to individual user time entries if Reports API fails
            self.logger.warning("Reports API failed, falling back to individual user queries")
            return self._get_time_entries_fallback_with_clients(workspace_id, start_date, end_date)
    
    def _get_time_entries_fallback_with_clients(self, workspace_id: int, 
                                               start_date: Optional[str], 
                                               end_date: Optional[str]) -> List[TimeEntry]:
        """Fallback method to get time entries with client info for all workspace users."""
        # Build client-project mapping
        client_mapping = self._build_client_project_mapping(workspace_id)
        
        all_entries = []
        
        # Get workspace users
        users = self.get_workspace_users(workspace_id)
        
        for user in users:
            try:
                # Get user's time entries
                user_entries = self._get_user_time_entries(user['id'], start_date, end_date)
                
                # Add client information to each entry
                for entry in user_entries:
                    if entry.project_id and entry.project_id in client_mapping:
                        client_info = client_mapping[entry.project_id]
                        entry.client_id = client_info['client_id']
                        entry.client_name = client_info['client_name']
                    else:
                        entry.client_id = None
                        entry.client_name = 'No Client'
                
                all_entries.extend(user_entries)
                
            except TogglAPIError as e:
                self.logger.warning(f"Failed to get entries for user {user.get('name', user['id'])}: {e}")
                continue
        
        return all_entries
    
    def _get_user_time_entries(self, user_id: int, start_date: Optional[str], 
                              end_date: Optional[str]) -> List[TimeEntry]:
        """Get time entries for a specific user."""
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
    
    def generate_client_reports(self, workspace_id: int, start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> List[ClientReport]:
        """
        Generate client-based reports with member breakdowns.
        
        Args:
            workspace_id: Workspace ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List[ClientReport]: List of client reports with member breakdowns
        """
        # Get time entries with client information
        time_entries = self.get_workspace_time_entries_with_clients(workspace_id, start_date, end_date)
        
        # Group by client and member
        client_data = {}
        
        for entry in time_entries:
            # Only count positive durations (negative means running)
            if entry.duration <= 0:
                continue
                
            client_key = entry.client_id or 'no_client'
            client_name = entry.client_name or 'No Client'
            
            if client_key not in client_data:
                client_data[client_key] = {
                    'client_id': entry.client_id,
                    'client_name': client_name,
                    'total_duration': 0,
                    'billable_duration': 0,
                    'members': {}
                }
            
            # Add to client totals
            client_data[client_key]['total_duration'] += entry.duration
            if entry.billable:
                client_data[client_key]['billable_duration'] += entry.duration
            
            # Add to member data within client
            member_key = entry.user_id
            if member_key not in client_data[client_key]['members']:
                client_data[client_key]['members'][member_key] = {
                    'user_id': entry.user_id,
                    'user_name': entry.user_name,
                    'total_duration': 0,
                    'billable_duration': 0,
                    'entry_count': 0
                }
            
            client_data[client_key]['members'][member_key]['total_duration'] += entry.duration
            if entry.billable:
                client_data[client_key]['members'][member_key]['billable_duration'] += entry.duration
            client_data[client_key]['members'][member_key]['entry_count'] += 1
        
        # Convert to ClientReport objects
        client_reports = []
        for client_key, client_info in client_data.items():
            # Create member reports
            member_reports = []
            for member_info in client_info['members'].values():
                member_reports.append(MemberClientReport(
                    user_id=member_info['user_id'],
                    user_name=member_info['user_name'],
                    client_id=client_info['client_id'],
                    client_name=client_info['client_name'],
                    total_duration_seconds=member_info['total_duration'],
                    billable_duration_seconds=member_info['billable_duration'],
                    entry_count=member_info['entry_count']
                ))
            
            # Sort members by total hours descending
            member_reports.sort(key=lambda m: m.total_hours, reverse=True)
            
            # Create client report
            client_reports.append(ClientReport(
                client_id=client_info['client_id'],
                client_name=client_info['client_name'],
                total_duration_seconds=client_info['total_duration'],
                billable_duration_seconds=client_info['billable_duration'],
                member_reports=member_reports
            ))
        
        # Sort clients by total hours descending
        client_reports.sort(key=lambda c: c.total_hours, reverse=True)
        
        return client_reports