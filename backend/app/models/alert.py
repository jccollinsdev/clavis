from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AlertBase(BaseModel):
    position_ticker: Optional[str] = None
    type: str  # grade_change | major_event | portfolio_grade_change | digest_ready
    previous_grade: Optional[str] = None
    new_grade: Optional[str] = None
    event_hash: Optional[str] = None
    analysis_run_id: Optional[str] = None
    change_reason: Optional[str] = None
    change_details: Optional[dict] = None
    message: str


class AlertCreate(AlertBase):
    pass


class Alert(AlertBase):
    id: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True
