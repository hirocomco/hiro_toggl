"""
API endpoints for settings management.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date

from app.models.database import get_db
from app.services.setting_service import SettingService
from app.schemas.settings import (
    SettingCreate, SettingUpdate, SettingResponse, SettingBulkCreate, 
    SettingBulkResponse, SettingQuery, SettingValueResponse,
    CategorySettingsResponse, SettingHistoryResponse, SettingCategory,
    SettingScope, SystemSettingsResponse, ApplicationDefaults,
    SettingValidationRequest, SettingValidationResponse
)


router = APIRouter(prefix="/api/settings", tags=["settings"])


def get_setting_service(db: Session = Depends(get_db)) -> SettingService:
    """Dependency to get SettingService."""
    return SettingService(db)


@router.post("/", response_model=SettingResponse, status_code=status.HTTP_201_CREATED)
async def create_setting(
    setting_data: SettingCreate,
    setting_service: SettingService = Depends(get_setting_service)
):
    """Create or update a setting."""
    try:
        setting = setting_service.set_setting(
            key=setting_data.key,
            value=setting_data.value,
            data_type=setting_data.data_type.value,
            workspace_id=setting_data.workspace_id,
            client_id=setting_data.client_id,
            category=setting_data.category.value,
            description=setting_data.description,
            is_readonly=setting_data.is_readonly,
            effective_date=setting_data.effective_date
        )
        
        return SettingResponse(
            id=setting.id,
            key=setting.key,
            value=setting.value,
            typed_value=setting.typed_value,
            data_type=setting.data_type,
            category=setting.category,
            scope=setting.scope,
            workspace_id=setting.workspace_id,
            client_id=setting.client_id,
            description=setting.description,
            is_readonly=setting.is_readonly,
            effective_date=setting.effective_date,
            created_at=setting.created_at,
            updated_at=setting.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create setting: {str(e)}")


@router.get("/value", response_model=SettingValueResponse)
async def get_setting_value(
    key: str = Query(..., description="Setting key"),
    workspace_id: Optional[int] = Query(None, description="Workspace ID"),
    client_id: Optional[int] = Query(None, description="Client ID"),
    category: Optional[SettingCategory] = Query(None, description="Setting category"),
    effective_date: Optional[date] = Query(None, description="Effective date"),
    setting_service: SettingService = Depends(get_setting_service)
):
    """Get a setting value with hierarchical resolution."""
    try:
        setting = setting_service.get_setting(
            key=key,
            workspace_id=workspace_id,
            client_id=client_id,
            category=category.value if category else None,
            effective_date=effective_date
        )
        
        if not setting:
            raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
        
        return SettingValueResponse(
            key=setting.key,
            value=setting.typed_value,
            data_type=setting.data_type,
            resolved_from=setting.scope,
            effective_date=setting.effective_date
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get setting: {str(e)}")


@router.get("/category/{category}", response_model=CategorySettingsResponse)
async def get_category_settings(
    category: SettingCategory,
    workspace_id: Optional[int] = Query(None, description="Workspace ID"),
    client_id: Optional[int] = Query(None, description="Client ID"),
    include_metadata: bool = Query(False, description="Include setting metadata"),
    effective_date: Optional[date] = Query(None, description="Effective date"),
    setting_service: SettingService = Depends(get_setting_service)
):
    """Get all settings in a category with hierarchical resolution."""
    try:
        settings = setting_service.get_settings_by_category(
            category=category.value,
            workspace_id=workspace_id,
            client_id=client_id,
            effective_date=effective_date
        )
        
        metadata = None
        if include_metadata:
            # Get full setting objects for metadata
            all_settings = setting_service.get_all_settings(
                workspace_id=workspace_id,
                category=category.value
            )
            metadata = {
                s.key: SettingResponse(
                    id=s.id,
                    key=s.key,
                    value=s.value,
                    typed_value=s.typed_value,
                    data_type=s.data_type,
                    category=s.category,
                    scope=s.scope,
                    workspace_id=s.workspace_id,
                    client_id=s.client_id,
                    description=s.description,
                    is_readonly=s.is_readonly,
                    effective_date=s.effective_date,
                    created_at=s.created_at,
                    updated_at=s.updated_at
                ) for s in all_settings
            }
        
        return CategorySettingsResponse(
            category=category,
            workspace_id=workspace_id,
            client_id=client_id,
            settings=settings,
            metadata=metadata
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get category settings: {str(e)}")


@router.get("/workspace/{workspace_id}")
async def get_workspace_settings(
    workspace_id: int,
    category: Optional[SettingCategory] = Query(None, description="Filter by category"),
    include_system: bool = Query(True, description="Include system defaults"),
    setting_service: SettingService = Depends(get_setting_service)
):
    """Get all settings for a workspace."""
    try:
        workspace_settings = setting_service.get_all_settings(
            workspace_id=workspace_id,
            category=category.value if category else None,
            scope=SettingScope.WORKSPACE.value
        )
        
        result = {
            "workspace_id": workspace_id,
            "settings": {}
        }
        
        # Group by category
        for setting in workspace_settings:
            if setting.category not in result["settings"]:
                result["settings"][setting.category] = {}
            
            result["settings"][setting.category][setting.key] = {
                "value": setting.typed_value,
                "data_type": setting.data_type,
                "description": setting.description,
                "effective_date": setting.effective_date.isoformat(),
                "is_readonly": setting.is_readonly
            }
        
        # Add system defaults if requested
        if include_system:
            system_settings = setting_service.get_all_settings(scope=SettingScope.SYSTEM.value)
            
            if "system_defaults" not in result["settings"]:
                result["settings"]["system_defaults"] = {}
            
            for setting in system_settings:
                # Only include if not overridden at workspace level
                workspace_override = setting_service.get_setting(
                    setting.key, workspace_id, effective_date=setting.effective_date
                )
                if not workspace_override or workspace_override.scope != SettingScope.WORKSPACE.value:
                    result["settings"]["system_defaults"][setting.key] = {
                        "value": setting.typed_value,
                        "data_type": setting.data_type,
                        "description": setting.description,
                        "effective_date": setting.effective_date.isoformat(),
                        "is_readonly": setting.is_readonly
                    }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workspace settings: {str(e)}")


@router.put("/{setting_id}", response_model=SettingResponse)
async def update_setting(
    setting_id: int,
    setting_data: SettingUpdate,
    setting_service: SettingService = Depends(get_setting_service)
):
    """Update an existing setting."""
    try:
        # Get existing setting
        db = setting_service.db
        from app.models.models import Setting
        existing_setting = db.query(Setting).filter(Setting.id == setting_id).first()
        if not existing_setting:
            raise HTTPException(status_code=404, detail="Setting not found")
        
        # Update fields if provided
        if setting_data.value is not None:
            updated_setting = setting_service.set_setting(
                key=existing_setting.key,
                value=setting_data.value,
                data_type=setting_data.data_type.value if setting_data.data_type else existing_setting.data_type,
                workspace_id=existing_setting.workspace_id,
                client_id=existing_setting.client_id,
                category=setting_data.category.value if setting_data.category else existing_setting.category,
                description=setting_data.description if setting_data.description is not None else existing_setting.description,
                effective_date=setting_data.effective_date or existing_setting.effective_date
            )
        else:
            updated_setting = existing_setting
        
        return SettingResponse(
            id=updated_setting.id,
            key=updated_setting.key,
            value=updated_setting.value,
            typed_value=updated_setting.typed_value,
            data_type=updated_setting.data_type,
            category=updated_setting.category,
            scope=updated_setting.scope,
            workspace_id=updated_setting.workspace_id,
            client_id=updated_setting.client_id,
            description=updated_setting.description,
            is_readonly=updated_setting.is_readonly,
            effective_date=updated_setting.effective_date,
            created_at=updated_setting.created_at,
            updated_at=updated_setting.updated_at
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update setting: {str(e)}")


@router.delete("/{setting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    setting_id: int,
    setting_service: SettingService = Depends(get_setting_service)
):
    """Delete a setting."""
    try:
        success = setting_service.delete_setting(setting_id)
        if not success:
            raise HTTPException(status_code=404, detail="Setting not found")
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete setting: {str(e)}")


@router.post("/bulk", response_model=SettingBulkResponse)
async def bulk_create_settings(
    bulk_data: SettingBulkCreate,
    setting_service: SettingService = Depends(get_setting_service)
):
    """Create multiple settings in a single transaction."""
    try:
        settings_data = []
        for setting in bulk_data.settings:
            setting_dict = {
                "key": setting.key,
                "value": setting.value,
                "data_type": setting.data_type.value,
                "category": setting.category.value,
                "workspace_id": setting.workspace_id or bulk_data.workspace_id,
                "client_id": setting.client_id or bulk_data.client_id,
                "description": setting.description,
                "is_readonly": setting.is_readonly,
                "effective_date": setting.effective_date or bulk_data.effective_date
            }
            settings_data.append(setting_dict)
        
        created_settings = setting_service.bulk_set_settings(
            settings_data=settings_data,
            workspace_id=bulk_data.workspace_id,
            client_id=bulk_data.client_id,
            effective_date=bulk_data.effective_date
        )
        
        response_settings = []
        created_count = 0
        updated_count = 0
        
        for setting in created_settings:
            response_settings.append(SettingResponse(
                id=setting.id,
                key=setting.key,
                value=setting.value,
                typed_value=setting.typed_value,
                data_type=setting.data_type,
                category=setting.category,
                scope=setting.scope,
                workspace_id=setting.workspace_id,
                client_id=setting.client_id,
                description=setting.description,
                is_readonly=setting.is_readonly,
                effective_date=setting.effective_date,
                created_at=setting.created_at,
                updated_at=setting.updated_at
            ))
            
            # Check if this was a creation or update
            if setting.created_at == setting.updated_at:
                created_count += 1
            else:
                updated_count += 1
        
        return SettingBulkResponse(
            created_count=created_count,
            updated_count=updated_count,
            settings=response_settings
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bulk create settings: {str(e)}")


@router.get("/history/{key}", response_model=SettingHistoryResponse)
async def get_setting_history(
    key: str,
    workspace_id: Optional[int] = Query(None, description="Workspace ID"),
    client_id: Optional[int] = Query(None, description="Client ID"),
    setting_service: SettingService = Depends(get_setting_service)
):
    """Get setting history for a specific key and scope."""
    try:
        history = setting_service.get_setting_history(
            key=key,
            workspace_id=workspace_id,
            client_id=client_id
        )
        
        history_responses = []
        for setting in history:
            history_responses.append(SettingResponse(
                id=setting.id,
                key=setting.key,
                value=setting.value,
                typed_value=setting.typed_value,
                data_type=setting.data_type,
                category=setting.category,
                scope=setting.scope,
                workspace_id=setting.workspace_id,
                client_id=setting.client_id,
                description=setting.description,
                is_readonly=setting.is_readonly,
                effective_date=setting.effective_date,
                created_at=setting.created_at,
                updated_at=setting.updated_at
            ))
        
        return SettingHistoryResponse(
            key=key,
            workspace_id=workspace_id,
            client_id=client_id,
            history=history_responses
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get setting history: {str(e)}")


@router.post("/validate", response_model=SettingValidationResponse)
async def validate_setting(
    validation_request: SettingValidationRequest
):
    """Validate a setting value for a given data type."""
    try:
        value = validation_request.value
        data_type = validation_request.data_type
        
        # Try to convert the value
        if data_type == "integer":
            converted_value = int(value)
        elif data_type == "float":
            converted_value = float(value)
        elif data_type == "boolean":
            if isinstance(value, bool):
                converted_value = value
            elif isinstance(value, str):
                converted_value = value.lower() in ('true', '1', 'yes', 'on')
            else:
                converted_value = bool(value)
        elif data_type == "json":
            import json
            if isinstance(value, (dict, list)):
                converted_value = value
            else:
                converted_value = json.loads(str(value))
        else:  # string
            converted_value = str(value)
        
        return SettingValidationResponse(
            is_valid=True,
            converted_value=converted_value
        )
        
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        return SettingValidationResponse(
            is_valid=False,
            error_message=f"Invalid value for type {validation_request.data_type.value}: {str(e)}"
        )


@router.get("/system/overview", response_model=SystemSettingsResponse)
async def get_system_overview(
    setting_service: SettingService = Depends(get_setting_service)
):
    """Get system-wide settings overview."""
    try:
        all_settings = setting_service.get_all_settings()
        
        by_category = {}
        by_scope = {}
        readonly_count = 0
        
        for setting in all_settings:
            # Count by category
            if setting.category not in by_category:
                by_category[setting.category] = 0
            by_category[setting.category] += 1
            
            # Count by scope
            if setting.scope not in by_scope:
                by_scope[setting.scope] = 0
            by_scope[setting.scope] += 1
            
            # Count readonly
            if setting.is_readonly:
                readonly_count += 1
        
        # Get recent changes (last 10)
        recent_settings = setting_service.get_all_settings()
        recent_settings.sort(key=lambda x: x.updated_at, reverse=True)
        recent_changes = []
        
        for setting in recent_settings[:10]:
            recent_changes.append(SettingResponse(
                id=setting.id,
                key=setting.key,
                value=setting.value,
                typed_value=setting.typed_value,
                data_type=setting.data_type,
                category=setting.category,
                scope=setting.scope,
                workspace_id=setting.workspace_id,
                client_id=setting.client_id,
                description=setting.description,
                is_readonly=setting.is_readonly,
                effective_date=setting.effective_date,
                created_at=setting.created_at,
                updated_at=setting.updated_at
            ))
        
        return SystemSettingsResponse(
            total_settings=len(all_settings),
            by_category=by_category,
            by_scope=by_scope,
            readonly_count=readonly_count,
            recent_changes=recent_changes
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system overview: {str(e)}")


@router.post("/initialize/workspace/{workspace_id}")
async def initialize_workspace_defaults(
    workspace_id: int,
    setting_service: SettingService = Depends(get_setting_service)
):
    """Initialize default settings for a workspace."""
    try:
        # Create workspace default settings
        settings_data = []
        for default in ApplicationDefaults.WORKSPACE_DEFAULTS:
            setting_dict = default.copy()
            setting_dict["workspace_id"] = workspace_id
            setting_dict["scope"] = "workspace"
            settings_data.append(setting_dict)
        
        created_settings = setting_service.bulk_set_settings(
            settings_data=settings_data,
            workspace_id=workspace_id
        )
        
        return {
            "workspace_id": workspace_id,
            "initialized_settings": len(created_settings),
            "settings": [s.key for s in created_settings]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize workspace defaults: {str(e)}")


@router.post("/initialize/system")
async def initialize_system_defaults(
    setting_service: SettingService = Depends(get_setting_service)
):
    """Initialize system default settings."""
    try:
        settings_data = ApplicationDefaults.SYSTEM_DEFAULTS.copy()
        
        created_settings = setting_service.bulk_set_settings(settings_data=settings_data)
        
        return {
            "initialized_settings": len(created_settings),
            "settings": [s.key for s in created_settings]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize system defaults: {str(e)}")