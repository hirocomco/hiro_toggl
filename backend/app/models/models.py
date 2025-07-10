"""
SQLAlchemy models for the Toggl Client Reports application.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Numeric, Text, ForeignKey, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, date
from typing import Optional

from .database import Base


class Client(Base):
    """Database model for Toggl clients."""
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    toggl_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    notes = Column(Text)
    external_reference = Column(String(255))
    archived = Column(Boolean, default=False)
    workspace_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    projects = relationship("Project", back_populates="client")
    rates = relationship("Rate", back_populates="client")

    def __repr__(self):
        return f"<Client(id={self.id}, toggl_id={self.toggl_id}, name='{self.name}')>"


class Project(Base):
    """Database model for Toggl projects."""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    toggl_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    workspace_id = Column(Integer, nullable=False, index=True)
    billable = Column(Boolean, default=False)
    is_private = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    color = Column(String(7))  # Hex color code
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    client = relationship("Client", back_populates="projects")
    time_entries = relationship("TimeEntryCache", back_populates="project")

    def __repr__(self):
        return f"<Project(id={self.id}, toggl_id={self.toggl_id}, name='{self.name}')>"


class Member(Base):
    """Database model for team members."""
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    toggl_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True)
    workspace_id = Column(Integer, nullable=False, index=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    rates = relationship("Rate", back_populates="member")
    time_entries = relationship("TimeEntryCache", back_populates="user", foreign_keys="TimeEntryCache.user_id", primaryjoin="Member.toggl_id == TimeEntryCache.user_id")

    def __repr__(self):
        return f"<Member(id={self.id}, toggl_id={self.toggl_id}, name='{self.name}')>"


class Rate(Base):
    """Database model for hourly rates (default and client-specific)."""
    __tablename__ = "rates"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)  # NULL for default rate
    hourly_rate_usd = Column(Numeric(10, 2))
    hourly_rate_eur = Column(Numeric(10, 2))
    effective_date = Column(Date, nullable=False, default=func.current_date(), index=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    member = relationship("Member", back_populates="rates")
    client = relationship("Client", back_populates="rates")

    # Unique constraint on member, client, and effective date
    __table_args__ = (
        {"extend_existing": True}
    )

    def __repr__(self):
        client_info = f"client_id={self.client_id}" if self.client_id else "default"
        return f"<Rate(member_id={self.member_id}, {client_info}, usd=${self.hourly_rate_usd})>"


class TimeEntryCache(Base):
    """Database model for cached time entries from Toggl."""
    __tablename__ = "time_entries_cache"

    id = Column(Integer, primary_key=True, index=True)
    toggl_id = Column(Integer, unique=True, nullable=False, index=True)
    description = Column(Text)
    duration = Column(Integer, nullable=False)  # Duration in seconds
    start_time = Column(DateTime, nullable=False, index=True)
    stop_time = Column(DateTime)
    user_id = Column(Integer, nullable=False, index=True)
    user_name = Column(String(255))
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    project_name = Column(String(255))
    client_id = Column(Integer, index=True)
    client_name = Column(String(255))
    workspace_id = Column(Integer, nullable=False, index=True)
    billable = Column(Boolean, default=False)
    tags = Column(ARRAY(String))  # PostgreSQL array of tags
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    sync_date = Column(Date, default=func.current_date(), index=True)

    # Relationships
    project = relationship("Project", back_populates="time_entries")
    user = relationship("Member", foreign_keys=[user_id], primaryjoin="TimeEntryCache.user_id == Member.toggl_id")

    def __repr__(self):
        return f"<TimeEntryCache(id={self.id}, toggl_id={self.toggl_id}, duration={self.duration}s)>"

    @property
    def duration_hours(self) -> float:
        """Get duration in hours."""
        return self.duration / 3600.0 if self.duration > 0 else 0.0


class SyncLog(Base):
    """Database model for tracking data synchronization."""
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, nullable=False, index=True)
    sync_type = Column(String(50), nullable=False)  # 'clients', 'projects', 'members', 'time_entries'
    start_time = Column(DateTime, nullable=False, default=func.current_timestamp())
    end_time = Column(DateTime)
    status = Column(String(20), nullable=False, default='running')  # 'running', 'completed', 'failed'
    records_processed = Column(Integer, default=0)
    records_added = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    error_message = Column(Text)
    date_range_start = Column(Date)  # For time entries sync
    date_range_end = Column(Date)    # For time entries sync

    def __repr__(self):
        return f"<SyncLog(id={self.id}, type={self.sync_type}, status={self.status})>"