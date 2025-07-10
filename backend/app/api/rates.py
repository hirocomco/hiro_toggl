"""
API endpoints for rate management.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field

from app.models.database import get_db
from app.services.rate_service import RateService
from app.models.models import Rate, Member, Client


router = APIRouter(prefix="/api/rates", tags=["rates"])


# Pydantic models for request/response
class RateCreate(BaseModel):
    member_id: int
    client_id: Optional[int] = None
    hourly_rate_usd: Optional[Decimal] = Field(None, ge=0, le=10000)
    hourly_rate_eur: Optional[Decimal] = Field(None, ge=0, le=10000)
    effective_date: Optional[date] = None

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v else None
        }


class RateUpdate(BaseModel):
    hourly_rate_usd: Optional[Decimal] = Field(None, ge=0, le=10000)
    hourly_rate_eur: Optional[Decimal] = Field(None, ge=0, le=10000)
    effective_date: Optional[date] = None

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v else None
        }


class RateResponse(BaseModel):
    id: int
    member_id: int
    member_name: Optional[str] = None
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    hourly_rate_usd: Optional[float] = None
    hourly_rate_eur: Optional[float] = None
    effective_date: date
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class MemberRatesResponse(BaseModel):
    member_id: int
    member_name: str
    default_rate: Optional[dict] = None
    client_rates: dict = {}


class EarningsCalculation(BaseModel):
    duration_seconds: int
    currency: str = Field(default="usd", regex="^(usd|eur)$")
    client_id: Optional[int] = None
    work_date: Optional[date] = None


class EarningsResponse(BaseModel):
    member_id: int
    duration_seconds: int
    duration_hours: float
    hourly_rate: Optional[float]
    earnings: Optional[float]
    currency: str


def get_rate_service(db: Session = Depends(get_db)) -> RateService:
    """Dependency to get RateService."""
    return RateService(db)


@router.post("/", response_model=RateResponse, status_code=status.HTTP_201_CREATED)
async def create_rate(
    rate_data: RateCreate,
    rate_service: RateService = Depends(get_rate_service)
):
    """
    Create or update a rate for a member.
    """
    try:
        rate = rate_service.set_member_rate(
            member_id=rate_data.member_id,
            hourly_rate_usd=rate_data.hourly_rate_usd,
            hourly_rate_eur=rate_data.hourly_rate_eur,
            client_id=rate_data.client_id,
            effective_date=rate_data.effective_date
        )
        
        # Get member and client names for response
        db = rate_service.db
        member = db.query(Member).filter(Member.id == rate.member_id).first()
        client = None
        if rate.client_id:
            client = db.query(Client).filter(Client.id == rate.client_id).first()
        
        return RateResponse(
            id=rate.id,
            member_id=rate.member_id,
            member_name=member.name if member else None,
            client_id=rate.client_id,
            client_name=client.name if client else None,
            hourly_rate_usd=float(rate.hourly_rate_usd) if rate.hourly_rate_usd else None,
            hourly_rate_eur=float(rate.hourly_rate_eur) if rate.hourly_rate_eur else None,
            effective_date=rate.effective_date,
            created_at=rate.created_at.isoformat(),
            updated_at=rate.updated_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create rate: {str(e)}")


@router.get("/member/{member_id}", response_model=MemberRatesResponse)
async def get_member_rates(
    member_id: int,
    rate_service: RateService = Depends(get_rate_service)
):
    """
    Get all rates for a specific member.
    """
    try:
        # Get member info
        db = rate_service.db
        member = db.query(Member).filter(Member.id == member_id).first()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        
        # Get current rates
        today = date.today()
        default_rate = rate_service.get_member_rate(member_id, None, today)
        
        # Get all client-specific rates
        client_rates = {}
        rates = rate_service.get_member_rates(member_id)
        
        for rate in rates:
            if rate.client_id is not None:
                if rate.client_id not in client_rates or rate.effective_date > client_rates[rate.client_id]['effective_date']:
                    client = db.query(Client).filter(Client.id == rate.client_id).first()
                    client_rates[rate.client_id] = {
                        'client_name': client.name if client else 'Unknown',
                        'hourly_rate_usd': float(rate.hourly_rate_usd) if rate.hourly_rate_usd else None,
                        'hourly_rate_eur': float(rate.hourly_rate_eur) if rate.hourly_rate_eur else None,
                        'effective_date': rate.effective_date
                    }
        
        return MemberRatesResponse(
            member_id=member_id,
            member_name=member.name,
            default_rate={
                'hourly_rate_usd': float(default_rate.hourly_rate_usd) if default_rate and default_rate.hourly_rate_usd else None,
                'hourly_rate_eur': float(default_rate.hourly_rate_eur) if default_rate and default_rate.hourly_rate_eur else None,
                'effective_date': default_rate.effective_date if default_rate else None
            } if default_rate else None,
            client_rates=client_rates
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get member rates: {str(e)}")


@router.get("/client/{client_id}", response_model=List[RateResponse])
async def get_client_rates(
    client_id: int,
    rate_service: RateService = Depends(get_rate_service)
):
    """
    Get all rates for a specific client.
    """
    try:
        # Verify client exists
        db = rate_service.db
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        rates = rate_service.get_client_rates(client_id)
        
        response_rates = []
        for rate in rates:
            member = db.query(Member).filter(Member.id == rate.member_id).first()
            
            response_rates.append(RateResponse(
                id=rate.id,
                member_id=rate.member_id,
                member_name=member.name if member else None,
                client_id=rate.client_id,
                client_name=client.name,
                hourly_rate_usd=float(rate.hourly_rate_usd) if rate.hourly_rate_usd else None,
                hourly_rate_eur=float(rate.hourly_rate_eur) if rate.hourly_rate_eur else None,
                effective_date=rate.effective_date,
                created_at=rate.created_at.isoformat(),
                updated_at=rate.updated_at.isoformat()
            ))
        
        return response_rates
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get client rates: {str(e)}")


@router.get("/workspace/{workspace_id}")
async def get_workspace_rates(
    workspace_id: int,
    rate_service: RateService = Depends(get_rate_service)
):
    """
    Get current rates for all members in a workspace.
    """
    try:
        rates_data = rate_service.get_all_current_rates(workspace_id)
        return {
            "workspace_id": workspace_id,
            "rates": rates_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workspace rates: {str(e)}")


@router.put("/{rate_id}", response_model=RateResponse)
async def update_rate(
    rate_id: int,
    rate_data: RateUpdate,
    rate_service: RateService = Depends(get_rate_service)
):
    """
    Update an existing rate.
    """
    try:
        db = rate_service.db
        rate = db.query(Rate).filter(Rate.id == rate_id).first()
        if not rate:
            raise HTTPException(status_code=404, detail="Rate not found")
        
        # Update the rate using the service
        updated_rate = rate_service.set_member_rate(
            member_id=rate.member_id,
            hourly_rate_usd=rate_data.hourly_rate_usd,
            hourly_rate_eur=rate_data.hourly_rate_eur,
            client_id=rate.client_id,
            effective_date=rate_data.effective_date or rate.effective_date
        )
        
        # Get member and client names for response
        member = db.query(Member).filter(Member.id == updated_rate.member_id).first()
        client = None
        if updated_rate.client_id:
            client = db.query(Client).filter(Client.id == updated_rate.client_id).first()
        
        return RateResponse(
            id=updated_rate.id,
            member_id=updated_rate.member_id,
            member_name=member.name if member else None,
            client_id=updated_rate.client_id,
            client_name=client.name if client else None,
            hourly_rate_usd=float(updated_rate.hourly_rate_usd) if updated_rate.hourly_rate_usd else None,
            hourly_rate_eur=float(updated_rate.hourly_rate_eur) if updated_rate.hourly_rate_eur else None,
            effective_date=updated_rate.effective_date,
            created_at=updated_rate.created_at.isoformat(),
            updated_at=updated_rate.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update rate: {str(e)}")


@router.delete("/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rate(
    rate_id: int,
    rate_service: RateService = Depends(get_rate_service)
):
    """
    Delete a rate.
    """
    try:
        success = rate_service.delete_rate(rate_id)
        if not success:
            raise HTTPException(status_code=404, detail="Rate not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete rate: {str(e)}")


@router.post("/calculate-earnings/{member_id}", response_model=EarningsResponse)
async def calculate_earnings(
    member_id: int,
    calculation: EarningsCalculation,
    rate_service: RateService = Depends(get_rate_service)
):
    """
    Calculate earnings for a member based on duration and rate.
    """
    try:
        # Verify member exists
        db = rate_service.db
        member = db.query(Member).filter(Member.id == member_id).first()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        
        # Calculate earnings
        earnings = rate_service.calculate_earnings(
            member_id=member_id,
            duration_seconds=calculation.duration_seconds,
            client_id=calculation.client_id,
            currency=calculation.currency,
            work_date=calculation.work_date
        )
        
        # Get the rate used for calculation
        rate = rate_service.get_member_rate(
            member_id, 
            calculation.client_id, 
            calculation.work_date or date.today()
        )
        
        hourly_rate = None
        if rate:
            hourly_rate = float(rate.hourly_rate_usd if calculation.currency == 'usd' else rate.hourly_rate_eur) if rate else None
        
        return EarningsResponse(
            member_id=member_id,
            duration_seconds=calculation.duration_seconds,
            duration_hours=round(calculation.duration_seconds / 3600, 2),
            hourly_rate=hourly_rate,
            earnings=float(earnings) if earnings else None,
            currency=calculation.currency
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate earnings: {str(e)}")


@router.get("/history/member/{member_id}")
async def get_rate_history(
    member_id: int,
    client_id: Optional[int] = None,
    rate_service: RateService = Depends(get_rate_service)
):
    """
    Get rate history for a member and client.
    """
    try:
        # Verify member exists
        db = rate_service.db
        member = db.query(Member).filter(Member.id == member_id).first()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        
        rates = rate_service.get_rate_history(member_id, client_id)
        
        response_rates = []
        for rate in rates:
            client = None
            if rate.client_id:
                client = db.query(Client).filter(Client.id == rate.client_id).first()
            
            response_rates.append(RateResponse(
                id=rate.id,
                member_id=rate.member_id,
                member_name=member.name,
                client_id=rate.client_id,
                client_name=client.name if client else None,
                hourly_rate_usd=float(rate.hourly_rate_usd) if rate.hourly_rate_usd else None,
                hourly_rate_eur=float(rate.hourly_rate_eur) if rate.hourly_rate_eur else None,
                effective_date=rate.effective_date,
                created_at=rate.created_at.isoformat(),
                updated_at=rate.updated_at.isoformat()
            ))
        
        return {
            "member_id": member_id,
            "member_name": member.name,
            "client_id": client_id,
            "rates": response_rates
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rate history: {str(e)}")