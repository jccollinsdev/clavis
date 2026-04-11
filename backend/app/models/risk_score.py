from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class RiskScoreBase(BaseModel):
    news_sentiment: Optional[float] = None
    macro_exposure: Optional[float] = None
    position_sizing: Optional[float] = None
    volatility_trend: Optional[float] = None
    total_score: Optional[float] = None
    grade: Optional[str] = None

    confidence: Optional[float] = None
    structural_base_score: Optional[float] = None
    macro_adjustment: Optional[float] = None
    event_adjustment: Optional[float] = None
    safety_score: Optional[float] = None

    reasoning: Optional[str] = None
    grade_reason: Optional[str] = None
    evidence_summary: Optional[str] = None
    dimension_rationale: Optional[dict] = None
    factor_breakdown: Optional[dict] = None
    mirofish_used: bool = False


class RiskScoreCreate(RiskScoreBase):
    position_id: str
    analysis_run_id: Optional[str] = None


class RiskScore(RiskScoreBase):
    id: str
    position_id: str
    analysis_run_id: Optional[str] = None
    calculated_at: datetime

    class Config:
        from_attributes = True
