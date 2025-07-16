"""
Rate management service for handling hourly rates (default and client-specific).
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from app.models.models import Rate, Member, Client
from app.models.database import get_db


class RateService:
    """Service for managing hourly rates."""

    def __init__(self, db: Session):
        self.db = db

    def get_member_rate(self, member_id: int, client_id: Optional[int] = None, 
                       effective_date: Optional[date] = None) -> Optional[Rate]:
        """
        Get the most current rate for a member and client.
        
        Args:
            member_id: Member ID
            client_id: Client ID (None for default rate)
            effective_date: Date to check rates for (defaults to today)
            
        Returns:
            Rate object or None if not found
        """
        if effective_date is None:
            effective_date = date.today()

        # Query for specific client rate first, then fall back to default
        query = self.db.query(Rate).filter(
            Rate.member_id == member_id,
            Rate.effective_date <= effective_date
        )

        if client_id is not None:
            # Look for client-specific rate first
            client_rate = query.filter(Rate.client_id == client_id).order_by(
                desc(Rate.effective_date)
            ).first()
            
            if client_rate:
                return client_rate

        # Fall back to default rate (client_id is NULL)
        default_rate = query.filter(Rate.client_id.is_(None)).order_by(
            desc(Rate.effective_date)
        ).first()

        return default_rate

    def set_member_rate(self, member_id: int, hourly_rate_usd: Optional[Decimal] = None,
                       hourly_rate_eur: Optional[Decimal] = None, client_id: Optional[int] = None,
                       effective_date: Optional[date] = None) -> Rate:
        """
        Set or update a rate for a member.
        
        Args:
            member_id: Member ID
            hourly_rate_usd: Hourly rate in USD
            hourly_rate_eur: Hourly rate in EUR
            client_id: Client ID (None for default rate)
            effective_date: When the rate becomes effective (defaults to today)
            
        Returns:
            Rate object
            
        Raises:
            ValueError: If member doesn't exist or invalid data
        """
        if effective_date is None:
            # Set to earliest time entry date to ensure rates apply to all historical data
            effective_date = date(2024, 7, 16)

        # Verify member exists
        member = self.db.query(Member).filter(Member.id == member_id).first()
        if not member:
            raise ValueError(f"Member with ID {member_id} not found")

        # Verify client exists if client_id is provided
        if client_id is not None:
            client = self.db.query(Client).filter(Client.id == client_id).first()
            if not client:
                raise ValueError(f"Client with ID {client_id} not found")

        # Check if rate already exists for this date
        existing_rate = self.db.query(Rate).filter(
            and_(
                Rate.member_id == member_id,
                Rate.client_id == client_id if client_id is not None else Rate.client_id.is_(None),
                Rate.effective_date == effective_date
            )
        ).first()

        if existing_rate:
            # Update existing rate
            if hourly_rate_usd is not None:
                existing_rate.hourly_rate_usd = hourly_rate_usd
            if hourly_rate_eur is not None:
                existing_rate.hourly_rate_eur = hourly_rate_eur
            existing_rate.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(existing_rate)
            return existing_rate
        else:
            # Create new rate
            new_rate = Rate(
                member_id=member_id,
                client_id=client_id,
                hourly_rate_usd=hourly_rate_usd,
                hourly_rate_eur=hourly_rate_eur,
                effective_date=effective_date
            )
            
            self.db.add(new_rate)
            self.db.commit()
            self.db.refresh(new_rate)
            return new_rate

    def get_member_rates(self, member_id: int) -> List[Rate]:
        """
        Get all rates for a member (default and client-specific).
        
        Args:
            member_id: Member ID
            
        Returns:
            List of Rate objects
        """
        return self.db.query(Rate).filter(
            Rate.member_id == member_id
        ).order_by(desc(Rate.effective_date)).all()

    def get_client_rates(self, client_id: int) -> List[Rate]:
        """
        Get all rates for a specific client.
        
        Args:
            client_id: Client ID
            
        Returns:
            List of Rate objects
        """
        return self.db.query(Rate).filter(
            Rate.client_id == client_id
        ).order_by(desc(Rate.effective_date)).all()

    def get_all_current_rates(self, workspace_id: int) -> Dict[int, Dict[str, Any]]:
        """
        Get current rates for all members in a workspace.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            Dictionary mapping member_id to rate information
        """
        today = date.today()
        rates_data = {}

        # Get all members in workspace
        members = self.db.query(Member).filter(Member.workspace_id == workspace_id).all()

        for member in members:
            # Get default rate
            default_rate = self.get_member_rate(member.id, None, today)
            
            # Get all client-specific rates
            client_rates = self.db.query(Rate).filter(
                and_(
                    Rate.member_id == member.id,
                    Rate.client_id.isnot(None),
                    Rate.effective_date <= today
                )
            ).order_by(desc(Rate.effective_date)).all()

            # Group client rates by client_id, keeping only the most recent
            latest_client_rates = {}
            for rate in client_rates:
                if rate.client_id not in latest_client_rates:
                    latest_client_rates[rate.client_id] = rate

            rates_data[member.id] = {
                'member_name': member.name,
                'default_rate': {
                    'usd': float(default_rate.hourly_rate_usd) if default_rate and default_rate.hourly_rate_usd else None,
                    'eur': float(default_rate.hourly_rate_eur) if default_rate and default_rate.hourly_rate_eur else None,
                    'effective_date': default_rate.effective_date.isoformat() if default_rate else None
                },
                'client_rates': {
                    client_id: {
                        'usd': float(rate.hourly_rate_usd) if rate.hourly_rate_usd else None,
                        'eur': float(rate.hourly_rate_eur) if rate.hourly_rate_eur else None,
                        'effective_date': rate.effective_date.isoformat()
                    }
                    for client_id, rate in latest_client_rates.items()
                }
            }

        return rates_data

    def calculate_earnings(self, member_id: int, duration_seconds: int, 
                          client_id: Optional[int] = None, currency: str = 'usd',
                          work_date: Optional[date] = None) -> Optional[Decimal]:
        """
        Calculate earnings for a given duration and member.
        
        Args:
            member_id: Member ID
            duration_seconds: Duration in seconds
            client_id: Client ID (None for default rate)
            currency: 'usd' or 'eur'
            work_date: Date of work (defaults to today)
            
        Returns:
            Calculated earnings or None if no rate found
        """
        if work_date is None:
            work_date = date.today()

        rate = self.get_member_rate(member_id, client_id, work_date)
        if not rate:
            return None

        hourly_rate = rate.hourly_rate_usd if currency == 'usd' else rate.hourly_rate_eur
        if not hourly_rate:
            return None

        hours = Decimal(duration_seconds) / Decimal(3600)
        return hours * hourly_rate

    def delete_rate(self, rate_id: int) -> bool:
        """
        Delete a rate.
        
        Args:
            rate_id: Rate ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        rate = self.db.query(Rate).filter(Rate.id == rate_id).first()
        if rate:
            self.db.delete(rate)
            self.db.commit()
            return True
        return False

    def get_rate_history(self, member_id: int, client_id: Optional[int] = None) -> List[Rate]:
        """
        Get rate history for a member and client.
        
        Args:
            member_id: Member ID
            client_id: Client ID (None for default rate)
            
        Returns:
            List of Rate objects ordered by effective date (newest first)
        """
        query = self.db.query(Rate).filter(Rate.member_id == member_id)
        
        if client_id is not None:
            query = query.filter(Rate.client_id == client_id)
        else:
            query = query.filter(Rate.client_id.is_(None))

        return query.order_by(desc(Rate.effective_date)).all()


def get_rate_service(db: Session = None) -> RateService:
    """
    Factory function to get RateService instance.
    
    Args:
        db: Database session (if None, will get from dependency)
        
    Returns:
        RateService instance
    """
    if db is None:
        db = next(get_db())
    return RateService(db)