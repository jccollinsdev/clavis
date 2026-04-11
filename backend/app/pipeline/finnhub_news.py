import finnhub
from datetime import datetime, timedelta
from typing import List
from ..config import get_settings

settings = get_settings()


def get_finnhub_client():
    return finnhub.Client(api_key=settings.finnhub_api_key)


async def fetch_company_news(tickers: List[str]) -> List[dict]:
    if not settings.finnhub_api_key:
        return []

    client = get_finnhub_client()
    articles = []
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

    for ticker in tickers:
        try:
            news = client.company_news(ticker, _from=from_date, to=to_date)
            for item in news[:10]:
                articles.append(
                    {
                        "id": str(item.get("id", "")),
                        "title": item.get("headline", ""),
                        "source": item.get("source", ""),
                        "url": item.get("url", ""),
                        "published_at": item.get("datetime", ""),
                        "summary": item.get("summary", ""),
                        "ticker": ticker,
                        "category": item.get("category", ""),
                    }
                )
        except Exception:
            continue

    return articles


async def fetch_market_news() -> List[dict]:
    if not settings.finnhub_api_key:
        return []

    client = get_finnhub_client()
    articles = []

    try:
        general = client.general_news("general", min_id=0)
        for item in general[:15]:
            articles.append(
                {
                    "id": str(item.get("id", "")),
                    "title": item.get("headline", ""),
                    "source": item.get("source", ""),
                    "url": item.get("url", ""),
                    "published_at": item.get("datetime", ""),
                    "summary": item.get("summary", ""),
                    "category": "market",
                }
            )
    except Exception:
        pass

    return articles
