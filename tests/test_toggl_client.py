"""
Unit tests for the Toggl API client.

These tests demonstrate the testing structure and provide basic coverage
for the main functionality.
"""

import pytest
from unittest.mock import Mock, patch
import requests
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from toggl_client import (
    TogglClient, TogglAPIError, MemberTimeTotal, TimeEntry,
    TogglRateLimitError, TogglAuthenticationError, TogglPaymentRequiredError,
    TogglEndpointGoneError, _validate_date_format, _validate_credentials,
    _sanitize_credentials
)


class TestTogglClient:
    """Test cases for TogglClient."""
    
    def test_init_with_api_token(self):
        """Test initialization with API token."""
        client = TogglClient(api_token="test_token")
        assert client.auth == ("test_token", "api_token")
    
    def test_init_with_email_password(self):
        """Test initialization with email/password."""
        client = TogglClient(email="test@example.com", password="password")
        assert client.auth == ("test@example.com", "password")
    
    def test_init_without_credentials(self):
        """Test initialization without credentials raises error."""
        with pytest.raises(TogglAuthenticationError):
            TogglClient()
    
    def test_init_with_invalid_api_token(self):
        """Test initialization with invalid API token raises error."""
        with pytest.raises(TogglAuthenticationError):
            TogglClient(api_token="short")
    
    def test_init_with_invalid_email(self):
        """Test initialization with invalid email raises error."""
        with pytest.raises(TogglAuthenticationError):
            TogglClient(email="invalid-email", password="password123")
    
    def test_init_with_short_password(self):
        """Test initialization with short password raises error."""
        with pytest.raises(TogglAuthenticationError):
            TogglClient(email="test@example.com", password="short")
    
    @patch('toggl_client.requests.Session.request')
    def test_make_request_success(self, mock_request):
        """Test successful API request."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"data": "test"}'
        mock_response.json.return_value = {"data": "test"}
        mock_request.return_value = mock_response
        
        client = TogglClient(api_token="test_token")
        result = client._make_request('GET', '/test')
        
        assert result == {"data": "test"}
        mock_request.assert_called_once()
    
    @patch('toggl_client.requests.Session.request')
    def test_make_request_http_error(self, mock_request):
        """Test HTTP error handling."""
        # Setup mock response with error
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_request.return_value = mock_response
        
        client = TogglClient(api_token="test_token")
        
        with pytest.raises(TogglAPIError):
            client._make_request('GET', '/test')
    
    @patch('toggl_client.requests.Session.request')
    def test_get_current_user(self, mock_request):
        """Test get_current_user method."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"id": 123, "fullname": "Test User"}'
        mock_response.json.return_value = {"id": 123, "fullname": "Test User"}
        mock_request.return_value = mock_response
        
        client = TogglClient(api_token="test_token")
        user = client.get_current_user()
        
        assert user["id"] == 123
        assert user["fullname"] == "Test User"
    
    @patch('toggl_client.requests.Session.request')
    def test_get_workspaces(self, mock_request):
        """Test get_workspaces method."""
        # Setup mock response
        workspaces_data = [
            {"id": 123, "name": "Test Workspace 1"},
            {"id": 456, "name": "Test Workspace 2"}
        ]
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'[{"id": 123, "name": "Test Workspace 1"}]'
        mock_response.json.return_value = workspaces_data
        mock_request.return_value = mock_response
        
        client = TogglClient(api_token="test_token")
        workspaces = client.get_workspaces()
        
        assert len(workspaces) == 2
        assert workspaces[0]["name"] == "Test Workspace 1"


class TestMemberTimeTotal:
    """Test cases for MemberTimeTotal dataclass."""
    
    def test_member_time_total_creation(self):
        """Test MemberTimeTotal creation and properties."""
        member = MemberTimeTotal(
            user_id=123,
            user_name="Test User",
            email="test@example.com",
            total_duration_seconds=7200,  # 2 hours
            billable_duration_seconds=3600,  # 1 hour
            entry_count=5
        )
        
        assert member.user_id == 123
        assert member.user_name == "Test User"
        assert member.total_hours == 2.0
        assert member.billable_hours == 1.0
        assert member.entry_count == 5
    
    def test_member_time_total_zero_duration(self):
        """Test MemberTimeTotal with zero duration."""
        member = MemberTimeTotal(
            user_id=123,
            user_name="Test User",
            email=None,
            total_duration_seconds=0,
            billable_duration_seconds=0,
            entry_count=0
        )
        
        assert member.total_hours == 0.0
        assert member.billable_hours == 0.0


class TestTimeEntry:
    """Test cases for TimeEntry dataclass."""
    
    def test_time_entry_creation(self):
        """Test TimeEntry creation."""
        entry = TimeEntry(
            id=123,
            description="Test task",
            duration=3600,  # 1 hour
            start="2023-01-01T10:00:00Z",
            stop="2023-01-01T11:00:00Z",
            user_id=456,
            user_name="Test User",
            project_id=789,
            project_name="Test Project",
            workspace_id=999,
            billable=True,
            tags=["development", "feature"]
        )
        
        assert entry.id == 123
        assert entry.description == "Test task"
        assert entry.duration == 3600
        assert entry.billable is True
        assert "development" in entry.tags


@pytest.fixture
def sample_time_entries():
    """Fixture providing sample time entries for testing."""
    return [
        {
            "id": 1,
            "description": "Task 1",
            "duration": 3600,
            "start": "2023-01-01T10:00:00Z",
            "stop": "2023-01-01T11:00:00Z",
            "user_id": 123,
            "user_name": "User 1",
            "workspace_id": 999,
            "billable": True
        },
        {
            "id": 2,
            "description": "Task 2",
            "duration": 1800,
            "start": "2023-01-01T14:00:00Z",
            "stop": "2023-01-01T14:30:00Z",
            "user_id": 123,
            "user_name": "User 1",
            "workspace_id": 999,
            "billable": False
        }
    ]


class TestIntegration:
    """Integration-style tests (mocked but more complete scenarios)."""
    
    @patch('toggl_client.requests.Session.request')
    def test_get_member_total_time_integration(self, mock_request, sample_time_entries):
        """Test get_member_total_time with sample data."""
        # Setup mock response for time entries
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'[]'
        mock_response.json.return_value = sample_time_entries
        mock_request.return_value = mock_response
        
        client = TogglClient(api_token="test_token")
        
        # Mock the get_time_entries method to return our sample data
        with patch.object(client, 'get_time_entries') as mock_get_entries:
            # Convert dict entries to TimeEntry objects
            time_entries = [
                TimeEntry(
                    id=entry["id"],
                    description=entry["description"],
                    duration=entry["duration"],
                    start=entry["start"],
                    stop=entry.get("stop"),
                    user_id=entry["user_id"],
                    user_name=entry["user_name"],
                    project_id=entry.get("project_id"),
                    project_name=entry.get("project_name", ""),
                    workspace_id=entry["workspace_id"],
                    billable=entry["billable"],
                    tags=entry.get("tags", [])
                )
                for entry in sample_time_entries
            ]
            
            mock_get_entries.return_value = time_entries
            
            # Test getting total time for specific user
            result = client.get_member_total_time(999, 123)
            
            assert isinstance(result, MemberTimeTotal)
            assert result.user_id == 123
            assert result.user_name == "User 1"
            assert result.total_duration_seconds == 5400  # 3600 + 1800
            assert result.billable_duration_seconds == 3600  # Only first entry is billable
            assert result.entry_count == 2
            assert result.total_hours == 1.5
            assert result.billable_hours == 1.0


class TestErrorHandling:
    """Test cases for enhanced error handling."""
    
    @patch('toggl_client.requests.Session.request')
    def test_rate_limit_error(self, mock_request):
        """Test 429 rate limit error handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_request.return_value = mock_response
        
        client = TogglClient(api_token="test_token_12345")
        
        with pytest.raises(TogglRateLimitError):
            client._make_request('GET', '/test')
    
    @patch('toggl_client.requests.Session.request')
    def test_authentication_error(self, mock_request):
        """Test 401/403 authentication error handling."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_request.return_value = mock_response
        
        client = TogglClient(api_token="test_token_12345")
        
        with pytest.raises(TogglAuthenticationError):
            client._make_request('GET', '/test')
    
    @patch('toggl_client.requests.Session.request')
    def test_payment_required_error(self, mock_request):
        """Test 402 payment required error handling."""
        mock_response = Mock()
        mock_response.status_code = 402
        mock_response.text = "Payment required"
        mock_request.return_value = mock_response
        
        client = TogglClient(api_token="test_token_12345")
        
        with pytest.raises(TogglPaymentRequiredError):
            client._make_request('GET', '/test')
    
    @patch('toggl_client.requests.Session.request')
    def test_endpoint_gone_error(self, mock_request):
        """Test 410 endpoint gone error handling."""
        mock_response = Mock()
        mock_response.status_code = 410
        mock_response.text = "Gone"
        mock_request.return_value = mock_response
        
        client = TogglClient(api_token="test_token_12345")
        
        with pytest.raises(TogglEndpointGoneError):
            client._make_request('GET', '/test')


class TestValidationFunctions:
    """Test cases for validation utility functions."""
    
    def test_validate_date_format_valid(self):
        """Test valid date format validation."""
        assert _validate_date_format("2023-01-01") is True
        assert _validate_date_format("2023-12-31") is True
    
    def test_validate_date_format_invalid(self):
        """Test invalid date format validation."""
        assert _validate_date_format("01-01-2023") is False
        assert _validate_date_format("2023/01/01") is False
        assert _validate_date_format("invalid") is False
    
    def test_validate_credentials_valid_token(self):
        """Test valid API token validation."""
        # Should not raise exception
        _validate_credentials(api_token="valid_token_123")
    
    def test_validate_credentials_invalid_token(self):
        """Test invalid API token validation."""
        with pytest.raises(TogglAuthenticationError):
            _validate_credentials(api_token="short")
    
    def test_validate_credentials_valid_email_password(self):
        """Test valid email/password validation."""
        # Should not raise exception
        _validate_credentials(email="test@example.com", password="password123")
    
    def test_validate_credentials_invalid_email(self):
        """Test invalid email validation."""
        with pytest.raises(TogglAuthenticationError):
            _validate_credentials(email="invalid-email", password="password123")
    
    def test_validate_credentials_invalid_password(self):
        """Test invalid password validation."""
        with pytest.raises(TogglAuthenticationError):
            _validate_credentials(email="test@example.com", password="short")
    
    def test_sanitize_credentials(self):
        """Test credential sanitization."""
        text_with_token = "Error: token abc123def456ghi789 failed"
        sanitized = _sanitize_credentials(text_with_token)
        assert "abc123def456ghi789" not in sanitized
        assert "[API_TOKEN]" in sanitized
        
        text_with_email = "Error: user@example.com authentication failed"
        sanitized = _sanitize_credentials(text_with_email)
        assert "user@example.com" not in sanitized
        assert "[EMAIL]" in sanitized


class TestDateValidation:
    """Test cases for date validation in client methods."""
    
    def test_get_time_entries_invalid_start_date(self):
        """Test invalid start date in get_time_entries."""
        client = TogglClient(api_token="test_token_12345")
        
        with pytest.raises(TogglAPIError, match="Invalid start_date format"):
            client.get_time_entries(start_date="01-01-2023")
    
    def test_get_time_entries_invalid_end_date(self):
        """Test invalid end date in get_time_entries."""
        client = TogglClient(api_token="test_token_12345")
        
        with pytest.raises(TogglAPIError, match="Invalid end_date format"):
            client.get_time_entries(end_date="2023/01/01")
    
    def test_get_member_total_time_invalid_date(self):
        """Test invalid date in get_member_total_time."""
        client = TogglClient(api_token="test_token_12345")
        
        with pytest.raises(TogglAPIError, match="Invalid start_date format"):
            client.get_member_total_time(123, start_date="invalid-date")


if __name__ == "__main__":
    pytest.main([__file__]) 