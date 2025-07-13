"""
Pydantic schemas for settings API requests and responses.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import date, datetime
from enum import Enum


class SettingDataType(str, Enum):
    """Supported data types for settings."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"


class SettingScope(str, Enum):
    """Setting scope levels."""
    SYSTEM = "system"
    WORKSPACE = "workspace"
    CLIENT = "client"


class SettingCategory(str, Enum):
    """Setting categories."""
    GENERAL = "general"
    WORKSPACE = "workspace"
    SYNC = "sync"
    UI = "ui"
    API = "api"
    NOTIFICATION = "notification"
    CURRENCY = "currency"
    RATE = "rate"


class SettingCreate(BaseModel):
    """Schema for creating a new setting."""
    key: str = Field(..., min_length=1, max_length=100, pattern="^[a-zA-Z0-9_.-]+$")
    value: Union[str, int, float, bool, dict, list]
    data_type: SettingDataType = SettingDataType.STRING
    category: SettingCategory = SettingCategory.GENERAL
    workspace_id: Optional[int] = None
    client_id: Optional[int] = None
    description: Optional[str] = Field(None, max_length=255)
    is_readonly: bool = False
    effective_date: Optional[date] = None

    @validator('key')
    def validate_key(cls, v):
        if v.startswith('_') or v.endswith('_'):
            raise ValueError('Setting key cannot start or end with underscore')
        return v.lower()

    @validator('client_id')
    def validate_client_scope(cls, v, values):
        if v is not None and values.get('workspace_id') is None:
            raise ValueError('workspace_id is required when client_id is specified')
        return v


class SettingUpdate(BaseModel):
    """Schema for updating an existing setting."""
    value: Optional[Union[str, int, float, bool, dict, list]] = None
    data_type: Optional[SettingDataType] = None
    category: Optional[SettingCategory] = None
    description: Optional[str] = Field(None, max_length=255)
    effective_date: Optional[date] = None


class SettingResponse(BaseModel):
    """Schema for setting responses."""
    id: int
    key: str
    value: str  # Raw string value from database
    typed_value: Union[str, int, float, bool, dict, list]  # Converted value
    data_type: SettingDataType
    category: SettingCategory
    scope: SettingScope
    workspace_id: Optional[int] = None
    client_id: Optional[int] = None
    description: Optional[str] = None
    is_readonly: bool
    effective_date: date
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SettingBulkCreate(BaseModel):
    """Schema for bulk setting creation."""
    settings: List[SettingCreate]
    workspace_id: Optional[int] = None  # Default workspace for all settings
    client_id: Optional[int] = None     # Default client for all settings
    effective_date: Optional[date] = None  # Default effective date


class SettingBulkResponse(BaseModel):
    """Schema for bulk setting responses."""
    created_count: int
    updated_count: int
    settings: List[SettingResponse]


class SettingQuery(BaseModel):
    """Schema for querying settings with hierarchical resolution."""
    key: str
    workspace_id: Optional[int] = None
    client_id: Optional[int] = None
    category: Optional[SettingCategory] = None
    effective_date: Optional[date] = None
    include_metadata: bool = False


class SettingValueResponse(BaseModel):
    """Schema for setting value responses."""
    key: str
    value: Union[str, int, float, bool, dict, list]
    data_type: SettingDataType
    resolved_from: SettingScope  # Which scope level provided the value
    effective_date: date


class CategorySettingsResponse(BaseModel):
    """Schema for category-based setting responses."""
    category: SettingCategory
    workspace_id: Optional[int] = None
    client_id: Optional[int] = None
    settings: Dict[str, Union[str, int, float, bool, dict, list]]
    metadata: Optional[Dict[str, SettingResponse]] = None


class SettingHistoryResponse(BaseModel):
    """Schema for setting history responses."""
    key: str
    workspace_id: Optional[int] = None
    client_id: Optional[int] = None
    history: List[SettingResponse]


class WorkspaceSettingsExport(BaseModel):
    """Schema for exporting workspace settings."""
    workspace_id: int
    export_date: datetime
    categories: Dict[SettingCategory, Dict[str, Any]]
    total_settings: int


class SettingsImport(BaseModel):
    """Schema for importing settings."""
    workspace_id: Optional[int] = None
    client_id: Optional[int] = None
    overwrite_existing: bool = False
    categories: Dict[SettingCategory, Dict[str, Any]]


class SettingValidationRequest(BaseModel):
    """Schema for validating setting values."""
    key: str
    value: Union[str, int, float, bool, dict, list]
    data_type: SettingDataType


class SettingValidationResponse(BaseModel):
    """Schema for setting validation responses."""
    is_valid: bool
    converted_value: Optional[Union[str, int, float, bool, dict, list]] = None
    error_message: Optional[str] = None


class SystemSettingsResponse(BaseModel):
    """Schema for system-wide settings overview."""
    total_settings: int
    by_category: Dict[SettingCategory, int]
    by_scope: Dict[SettingScope, int]
    readonly_count: int
    recent_changes: List[SettingResponse]


# Predefined setting configurations for common use cases
class ApplicationDefaults:
    """Default application settings."""
    
    WORKSPACE_DEFAULTS = [
        {
            "key": "default_currency",
            "value": "USD",
            "data_type": "string",
            "category": "currency",
            "description": "Default currency for workspace"
        },
        {
            "key": "auto_sync",
            "value": True,
            "data_type": "boolean",
            "category": "sync",
            "description": "Enable automatic data synchronization"
        },
        {
            "key": "sync_interval",
            "value": 30,
            "data_type": "integer",
            "category": "sync",
            "description": "Sync interval in minutes"
        },
        {
            "key": "notifications",
            "value": True,
            "data_type": "boolean",
            "category": "notification",
            "description": "Enable desktop notifications"
        },
        {
            "key": "workspace_id",
            "value": "",
            "data_type": "string",
            "category": "api",
            "description": "Toggl workspace ID"
        }
    ]

    SYSTEM_DEFAULTS = [
        {
            "key": "max_sync_retries",
            "value": 3,
            "data_type": "integer",
            "category": "sync",
            "description": "Maximum number of sync retries",
            "is_readonly": True
        },
        {
            "key": "api_rate_limit",
            "value": 1,
            "data_type": "float",
            "category": "api",
            "description": "API rate limit in requests per second",
            "is_readonly": True
        },
        {
            "key": "session_timeout",
            "value": 3600,
            "data_type": "integer",
            "category": "api",
            "description": "Session timeout in seconds",
            "is_readonly": True
        }
    ]