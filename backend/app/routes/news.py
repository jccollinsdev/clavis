from fastapi import APIRouter, Depends, Request

from ..services.news_feed_service import build_news_feed_bundle, get_news_article_bundle
from ..services.supabase import get_supabase

router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


@router.get("")
async def get_news(limit: int = 30, user_id: str = Depends(get_user_id)):
    supabase = get_supabase()
    return build_news_feed_bundle(supabase, user_id, limit=limit)


@router.get("/{article_id}")
async def get_news_article(article_id: str, user_id: str = Depends(get_user_id)):
    supabase = get_supabase()
    return get_news_article_bundle(supabase, user_id, article_id)
