from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EventNewsItem(BaseModel):
    id: str
    title: str
    source: Optional[str] = None
    published_at: Optional[datetime] = None
    tldr: Optional[str] = None
    what_it_means: Optional[str] = None
    key_implications: list[str] = Field(default_factory=list)
    follow_up_notes: list[str] = Field(default_factory=list)
    source_article_link: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
