from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DigestBase(BaseModel):
    content: str
    grade_summary: Optional[dict] = None
    overall_grade: Optional[str] = None
    overall_score: Optional[float] = None
    score_source: Optional[str] = None
    score_as_of: Optional[str] = None
    score_version: Optional[str] = None
    structured_sections: Optional[dict] = None
    summary: Optional[str] = None


class DigestCreate(DigestBase):
    analysis_run_id: Optional[str] = None


class Digest(DigestBase):
    id: str
    user_id: str
    analysis_run_id: Optional[str] = None
    generated_at: datetime

    class Config:
        from_attributes = True
