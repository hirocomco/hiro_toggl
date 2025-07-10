"""
Configuration settings for Toggl API integration.
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class TogglConfig:
    """Configuration for Toggl API client."""
    api_token: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    default_workspace_id: Optional[int] = None
    
    @classmethod
    def from_env(cls) -> 'TogglConfig':
        """Load configuration from environment variables."""
        return cls(
            api_token=os.getenv('TOGGL_API_TOKEN'),
            email=os.getenv('TOGGL_EMAIL'),
            password=os.getenv('TOGGL_PASSWORD'),
            default_workspace_id=int(os.getenv('TOGGL_WORKSPACE_ID', 0)) or None
        )
    
    def is_valid(self) -> bool:
        """Check if configuration has valid authentication."""
        return bool(self.api_token or (self.email and self.password))