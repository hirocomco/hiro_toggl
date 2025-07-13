"""
Setting management service for handling application settings with hierarchical scoping.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, or_
from typing import List, Optional, Dict, Any, Union
from datetime import date, datetime
import json

from app.models.models import Setting, Client
from app.models.database import get_db


class SettingService:
    """Service for managing application settings with hierarchical resolution."""

    def __init__(self, db: Session):
        self.db = db

    def get_setting(self, key: str, workspace_id: Optional[int] = None, 
                   client_id: Optional[int] = None, category: Optional[str] = None,
                   effective_date: Optional[date] = None) -> Optional[Setting]:
        """
        Get a setting with hierarchical resolution.
        Resolution order: client-specific → workspace → system
        
        Args:
            key: Setting key
            workspace_id: Workspace ID (None for system settings)
            client_id: Client ID (None for non-client specific)
            category: Setting category filter
            effective_date: Date to check settings for (defaults to today)
            
        Returns:
            Setting object or None if not found
        """
        if effective_date is None:
            effective_date = date.today()

        base_query = self.db.query(Setting).filter(
            Setting.key == key,
            Setting.effective_date <= effective_date
        )

        if category:
            base_query = base_query.filter(Setting.category == category)

        # Try client-specific setting first
        if client_id is not None and workspace_id is not None:
            client_setting = base_query.filter(
                Setting.client_id == client_id,
                Setting.workspace_id == workspace_id,
                Setting.scope == 'client'
            ).order_by(desc(Setting.effective_date)).first()
            
            if client_setting:
                return client_setting

        # Try workspace setting
        if workspace_id is not None:
            workspace_setting = base_query.filter(
                Setting.workspace_id == workspace_id,
                Setting.client_id.is_(None),
                Setting.scope == 'workspace'
            ).order_by(desc(Setting.effective_date)).first()
            
            if workspace_setting:
                return workspace_setting

        # Fall back to system setting
        system_setting = base_query.filter(
            Setting.workspace_id.is_(None),
            Setting.client_id.is_(None),
            Setting.scope == 'system'
        ).order_by(desc(Setting.effective_date)).first()

        return system_setting

    def get_setting_value(self, key: str, workspace_id: Optional[int] = None,
                         client_id: Optional[int] = None, category: Optional[str] = None,
                         default_value: Any = None, effective_date: Optional[date] = None) -> Any:
        """
        Get a setting value with type conversion and hierarchical resolution.
        
        Args:
            key: Setting key
            workspace_id: Workspace ID
            client_id: Client ID
            category: Setting category filter
            default_value: Default value if setting not found
            effective_date: Date to check settings for
            
        Returns:
            Typed setting value or default_value
        """
        setting = self.get_setting(key, workspace_id, client_id, category, effective_date)
        if setting:
            return setting.typed_value
        return default_value

    def set_setting(self, key: str, value: Any, data_type: str = 'string',
                   workspace_id: Optional[int] = None, client_id: Optional[int] = None,
                   category: str = 'general', description: Optional[str] = None,
                   is_readonly: bool = False, effective_date: Optional[date] = None) -> Setting:
        """
        Set or update a setting.
        
        Args:
            key: Setting key
            value: Setting value
            data_type: Value type ('string', 'integer', 'float', 'boolean', 'json')
            workspace_id: Workspace ID (None for system settings)
            client_id: Client ID (None for non-client specific)
            category: Setting category
            description: Human-readable description
            is_readonly: Whether setting is readonly
            effective_date: When the setting becomes effective (defaults to today)
            
        Returns:
            Setting object
            
        Raises:
            ValueError: If client doesn't exist or invalid data
        """
        if effective_date is None:
            effective_date = date.today()

        # Determine scope based on parameters
        if client_id is not None:
            scope = 'client'
            if workspace_id is None:
                raise ValueError("workspace_id is required for client-scoped settings")
            # Verify client exists
            client = self.db.query(Client).filter(Client.id == client_id).first()
            if not client:
                raise ValueError(f"Client with ID {client_id} not found")
        elif workspace_id is not None:
            scope = 'workspace'
        else:
            scope = 'system'

        # Convert value to string for storage
        if data_type == 'json':
            str_value = json.dumps(value)
        elif data_type == 'boolean':
            str_value = str(bool(value)).lower()
        else:
            str_value = str(value)

        # Check if setting already exists for this date and scope
        existing_setting = self.db.query(Setting).filter(
            and_(
                Setting.key == key,
                Setting.scope == scope,
                Setting.workspace_id == workspace_id if workspace_id is not None else Setting.workspace_id.is_(None),
                Setting.client_id == client_id if client_id is not None else Setting.client_id.is_(None),
                Setting.effective_date == effective_date
            )
        ).first()

        if existing_setting:
            # Update existing setting
            if existing_setting.is_readonly:
                raise ValueError(f"Setting '{key}' is readonly and cannot be modified")
            
            existing_setting.value = str_value
            existing_setting.data_type = data_type
            existing_setting.category = category
            if description is not None:
                existing_setting.description = description
            existing_setting.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(existing_setting)
            return existing_setting
        else:
            # Create new setting
            new_setting = Setting(
                key=key,
                value=str_value,
                data_type=data_type,
                category=category,
                scope=scope,
                workspace_id=workspace_id,
                client_id=client_id,
                description=description,
                is_readonly=is_readonly,
                effective_date=effective_date
            )
            
            self.db.add(new_setting)
            self.db.commit()
            self.db.refresh(new_setting)
            return new_setting

    def get_settings_by_category(self, category: str, workspace_id: Optional[int] = None,
                                client_id: Optional[int] = None, 
                                effective_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Get all settings in a category with hierarchical resolution.
        
        Args:
            category: Setting category
            workspace_id: Workspace ID
            client_id: Client ID
            effective_date: Date to check settings for
            
        Returns:
            Dictionary mapping setting keys to typed values
        """
        if effective_date is None:
            effective_date = date.today()

        # Get all possible setting keys in this category
        all_settings = self.db.query(Setting).filter(
            Setting.category == category,
            Setting.effective_date <= effective_date
        ).all()

        # Get unique keys
        unique_keys = set(setting.key for setting in all_settings)

        # Resolve each key hierarchically
        resolved_settings = {}
        for key in unique_keys:
            setting = self.get_setting(key, workspace_id, client_id, category, effective_date)
            if setting:
                resolved_settings[key] = setting.typed_value

        return resolved_settings

    def delete_setting(self, setting_id: int) -> bool:
        """
        Delete a setting.
        
        Args:
            setting_id: Setting ID to delete
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            ValueError: If setting is readonly
        """
        setting = self.db.query(Setting).filter(Setting.id == setting_id).first()
        if setting:
            if setting.is_readonly:
                raise ValueError(f"Setting '{setting.key}' is readonly and cannot be deleted")
            
            self.db.delete(setting)
            self.db.commit()
            return True
        return False

    def get_all_settings(self, workspace_id: Optional[int] = None, 
                        category: Optional[str] = None, 
                        scope: Optional[str] = None) -> List[Setting]:
        """
        Get all settings with optional filtering.
        
        Args:
            workspace_id: Filter by workspace ID
            category: Filter by category
            scope: Filter by scope ('system', 'workspace', 'client')
            
        Returns:
            List of Setting objects
        """
        query = self.db.query(Setting)

        if workspace_id is not None:
            query = query.filter(Setting.workspace_id == workspace_id)
        
        if category is not None:
            query = query.filter(Setting.category == category)
            
        if scope is not None:
            query = query.filter(Setting.scope == scope)

        return query.order_by(Setting.category, Setting.key, desc(Setting.effective_date)).all()

    def get_setting_history(self, key: str, workspace_id: Optional[int] = None,
                           client_id: Optional[int] = None) -> List[Setting]:
        """
        Get setting history for a specific key and scope.
        
        Args:
            key: Setting key
            workspace_id: Workspace ID
            client_id: Client ID
            
        Returns:
            List of Setting objects ordered by effective date (newest first)
        """
        query = self.db.query(Setting).filter(Setting.key == key)
        
        if client_id is not None:
            query = query.filter(Setting.client_id == client_id)
        elif workspace_id is not None:
            query = query.filter(
                Setting.workspace_id == workspace_id,
                Setting.client_id.is_(None)
            )
        else:
            query = query.filter(
                Setting.workspace_id.is_(None),
                Setting.client_id.is_(None)
            )

        return query.order_by(desc(Setting.effective_date)).all()

    def bulk_set_settings(self, settings_data: List[Dict[str, Any]], 
                         workspace_id: Optional[int] = None,
                         client_id: Optional[int] = None,
                         effective_date: Optional[date] = None) -> List[Setting]:
        """
        Set multiple settings in a single transaction.
        
        Args:
            settings_data: List of setting dictionaries with keys: key, value, data_type, category, etc.
            workspace_id: Default workspace ID for all settings
            client_id: Default client ID for all settings
            effective_date: Default effective date for all settings
            
        Returns:
            List of created/updated Setting objects
        """
        created_settings = []
        
        try:
            for setting_data in settings_data:
                setting = self.set_setting(
                    key=setting_data['key'],
                    value=setting_data['value'],
                    data_type=setting_data.get('data_type', 'string'),
                    workspace_id=setting_data.get('workspace_id', workspace_id),
                    client_id=setting_data.get('client_id', client_id),
                    category=setting_data.get('category', 'general'),
                    description=setting_data.get('description'),
                    is_readonly=setting_data.get('is_readonly', False),
                    effective_date=setting_data.get('effective_date', effective_date)
                )
                created_settings.append(setting)
            
            return created_settings
            
        except Exception as e:
            self.db.rollback()
            raise e


def get_setting_service(db: Session = None) -> SettingService:
    """
    Factory function to get SettingService instance.
    
    Args:
        db: Database session (if None, will get from dependency)
        
    Returns:
        SettingService instance
    """
    if db is None:
        db = next(get_db())
    return SettingService(db)