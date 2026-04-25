from pydantic import BaseModel
from typing import Any, Optional
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
    synced_from_brokerage: bool = False
    brokerage_authorization_id: Optional[str] = None
    brokerage_account_id: Optional[str] = None
    brokerage_last_synced_at: Optional[datetime] = None
    analysis_started_at: Optional[datetime] = None
    risk_grade: Optional[str] = None
    total_score: Optional[float] = None
    previous_grade: Optional[str] = None
    inferred_labels: Optional[list[str]] = None
    summary: Optional[str] = None
    last_analyzed_at: Optional[datetime] = None
    analysis_state: Optional[str] = None
    coverage_state: Optional[str] = None
    coverage_note: Optional[str] = None
    analysis_run_id: Optional[str] = None
    latest_analysis_run: Optional[dict[str, Any]] = None
    latest_refresh_job: Optional[dict[str, Any]] = None
    analysis_as_of: Optional[datetime] = None
    score_source: Optional[str] = None
    score_as_of: Optional[datetime] = None
    score_version: Optional[str] = None
    last_news_refresh_at: Optional[datetime] = None
    news_refresh_status: Optional[str] = None
    price_as_of: Optional[datetime] = None
    news_as_of: Optional[datetime] = None
    source: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HoldingWorkflowResponse(BaseModel):
    holding_id: str
    ticker: str
    analysis_state: str
    analysis_run_id: Optional[str] = None
    latest_refresh_job: Optional[dict[str, Any]] = None
    coverage_state: Optional[str] = None
    coverage_note: Optional[str] = None
    analysis_as_of: Optional[datetime] = None
    score_source: Optional[str] = None
    score_as_of: Optional[datetime] = None
    score_version: Optional[str] = None
    last_news_refresh_at: Optional[datetime] = None
    news_refresh_status: Optional[str] = None
    news_as_of: Optional[datetime] = None
    price_as_of: Optional[datetime] = None
    position: Optional[Position] = None
    source: Optional[str] = None
