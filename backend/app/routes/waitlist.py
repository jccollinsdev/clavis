from __future__ import annotations

import logging
import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from ..services.supabase import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter()

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class WaitlistSignup(BaseModel):
    email: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        if value is None:
            raise ValueError("Email is required")

        if not isinstance(value, str):
            value = str(value)

        value = value.strip().lower()
        if not value:
            raise ValueError("Email is required")

        if not EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address")

        return value


def _waitlist_context(request: Request) -> dict[str, str]:
    referrer = request.headers.get("referer") or request.headers.get("origin")
    user_agent = request.headers.get("user-agent")

    context: dict[str, str] = {"source": "website"}
    if referrer:
        context["referrer"] = referrer[:1024]
    if user_agent:
        context["user_agent"] = user_agent[:1024]
    return context


@router.post("")
async def join_waitlist(signup: WaitlistSignup, request: Request):
    email = signup.email
    supabase = get_supabase()

    existing = (
        supabase.table("waitlist_signups")
        .select("id")
        .eq("email", email)
        .limit(1)
        .execute()
        .data
        or []
    )

    if existing:
        return {
            "status": "duplicate",
            "message": "That email is already on the waitlist.",
        }

    payload = {"email": email, **_waitlist_context(request)}

    try:
        result = supabase.table("waitlist_signups").insert(payload).execute()
    except Exception as exc:
        logger.warning("waitlist_insert_failed: %s", exc)
        existing = (
            supabase.table("waitlist_signups")
            .select("id")
            .eq("email", email)
            .limit(1)
            .execute()
            .data
            or []
        )
        if existing:
            return {
                "status": "duplicate",
                "message": "That email is already on the waitlist.",
            }

        raise HTTPException(500, "Failed to join waitlist") from exc

    if not result.data:
        raise HTTPException(500, "Failed to join waitlist")

    return {"status": "success", "message": "You are on the waitlist."}
