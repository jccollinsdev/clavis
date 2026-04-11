from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PositionBase(BaseModel):
    ticker: str
    shares: float
    purchase_price: float
    archetype: str  # growth | value | cyclical | defensive | small_cap


class PositionCreate(PositionBase):
    pass


class PositionUpdate(BaseModel):
    ticker: Optional[str] = None
    shares: Optional[float] = None
    purchase_price: Optional[float] = None
    archetype: Optional[str] = None


class Position(PositionBase):
    id: str
    user_id: str
    current_price: Optional[float] = None
    analysis_started_at: Optional[datetime] = None
    risk_grade: Optional[str] = None
    total_score: Optional[float] = None
    previous_grade: Optional[str] = None
    inferred_labels: Optional[list[str]] = None
    summary: Optional[str] = None
    last_analyzed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
