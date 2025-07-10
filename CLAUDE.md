# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python library for integrating with the Toggl Track API v9 and Reports API v3. It provides functionality to retrieve time tracking data for workspace members, including total time tracked, billable hours, and detailed time entries.

## Development Commands

### Setup and Installation
```bash
# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt
```

### Key Dependencies Added in Phase 1 Improvements
- `backoff>=2.0.0`: Exponential backoff for rate limiting and retries
- `python-dateutil>=2.8.0`: Enhanced date/time parsing and validation

### Testing and Quality
```bash
# Run tests
pytest tests/

# Run tests with coverage
pytest --cov=src tests/

# Code formatting
black src/ config/ examples/

# Linting
flake8 src/ config/ examples/

# Type checking
mypy src/ config/ examples/
```

### Running Examples
```bash
# Set environment variables first
export TOGGL_API_TOKEN='your_api_token_here'
export TOGGL_WORKSPACE_ID='123456'  # Optional

# Run the example script
python examples/get_member_time_example.py

# Quick test
python quick_test.py
```

## Architecture

### Core Components

1. **TogglClient** (`src/toggl_client.py`): Main API client class
   - Handles authentication (API token or email/password)
   - Makes requests to both Track API v9 and Reports API v3
   - Implements rate limiting awareness and error handling
   - Provides fallback mechanisms for permission issues

2. **Configuration** (`config/config.py`): Environment-based configuration
   - Loads settings from environment variables
   - Supports both API token and email/password authentication
   - Handles workspace ID configuration

3. **Data Models**: Defined in `src/toggl_client.py`
   - `TimeEntry`: Represents individual time entries
   - `MemberTimeTotal`: Aggregated time data for users
   - `TogglAPIError`: Custom exception for API errors

### Key Methods

- `get_member_total_time()`: Main feature - aggregates time data for workspace members
- `get_workspace_time_entries()`: Retrieves all time entries for a workspace
- `get_time_entries()`: Gets time entries for authenticated user
- `get_current_user()` / `get_workspaces()`: Basic API interactions

### Enhanced Error Handling (Phase 1 Improvements)

**New Exception Classes:**
- `TogglRateLimitError`: For 429 rate limit responses
- `TogglAuthenticationError`: For 401/403 authentication failures
- `TogglPaymentRequiredError`: For 402 payment required responses
- `TogglEndpointGoneError`: For 410 gone endpoints

**Improved Error Handling:**
- Automatic credential sanitization in error messages
- Specific handling for different HTTP status codes
- No retry for 4xx errors (except rate limits)
- Automatic retry with exponential backoff for 5xx errors

### Authentication

The client supports two authentication methods:
1. **API Token** (recommended): `TOGGL_API_TOKEN` environment variable
2. **Email/Password**: `TOGGL_EMAIL` and `TOGGL_PASSWORD` environment variables

### API Integration

- **Track API v9**: Used for user/workspace data and individual time entries
- **Reports API v3**: Used for workspace-wide time entry queries and summaries
- **Rate Limiting**: Automatic 1 req/sec throttling with exponential backoff for 429 responses
- **Error Handling**: Comprehensive error handling with specific exceptions and fallback mechanisms
- **Input Validation**: Date format validation (YYYY-MM-DD) and credential validation

### Development Patterns

1. **Environment Configuration**: All settings loaded via environment variables or `.env` file
2. **Fallback Mechanisms**: If Reports API fails, falls back to individual user queries
3. **Data Aggregation**: Time entries are aggregated by user to calculate totals
4. **Error Recovery**: Graceful handling of permission issues and API failures

## Testing

- Test files should be placed in `tests/` directory
- Use pytest for running tests
- Current test file: `tests/test_toggl_client.py`
- Use pytest-mock for mocking API calls during tests

## Environment Variables

Required for authentication:
- `TOGGL_API_TOKEN`: Your Toggl API token (preferred)
- `TOGGL_EMAIL` / `TOGGL_PASSWORD`: Alternative authentication

Optional:
- `TOGGL_WORKSPACE_ID`: Default workspace ID to use

## Important Notes

- All time data is in UTC
- Duration calculations handle both positive durations and running timers (negative durations)
- The client includes permission-aware fallbacks for workspace operations
- **Phase 1 Improvements**: Automatic rate limiting, enhanced error handling, and input validation
- Date parameters must be in YYYY-MM-DD format
- Credentials are automatically validated and sanitized in error messages
- Rate limiting enforces 1 req/sec with automatic retry for 429 responses