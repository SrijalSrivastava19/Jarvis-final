"""
News service — Phase 2.2 "News Engine Upgrade".

Architecture:
top / world / india / technology / business / science  -> NewsData.io
ai       -> TechCrunch AI RSS (primary), NewsData.io keyword search (fallback)
sports   -> ESPN RSS

Replaces the Phase 2 implementation, which used BBC RSS for every category
except technology/ai (TechCrunch) and india (NDTV). BBC is no longer used
anywhere in this module.

Design notes:
- All network calls go through a single retrying, timeout-bound HTTP
    helper (`_http_get`) so every source gets the same resilience
    characteristics (3 attempts, exponential backoff, bounded timeout).
- Responses are cached in-process per category for `news_cache_seconds`
    (unchanged behavior from Phase 2).
- If a live fetch fails and a previous (stale) cached response exists,
    the stale response is served rather than surfacing an error — this is
    the "automatic fallback" behavior for transient outages. If there is
    no cache to fall back to, a `NewsServiceError` is raised, which the
    app's existing global exception handler converts to a 503 — identical
    to Phase 2 behavior in the total-failure case.
- Headlines are de-duplicated by normalized title before being returned,
    since NewsData.io and RSS feeds can both surface the same story from
    syndicated sources.
- `NewsItem` / `NewsResponse` schemas and the `/api/news/*` routes are
    completely unchanged; this file only changes how the data inside them
    is sourced.
"""
import asyncio
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import feedparser
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.exceptions import NewsServiceError
from app.logger import get_logger
from app.models.schemas import NewsItem, NewsResponse

logger = get_logger(__name__)

NEWSDATA_BASE_URL = "https://newsdata.io/api/1/latest"
TECHCRUNCH_AI_RSS = "https://techcrunch.com/category/artificial-intelligence/feed/"

# Categories served directly by NewsData.io, with their query params.
# "top" and "india" are intentionally *not* passed a `category` param:
# NewsData.io treats an omitted category as "top headlines", and india
# is filtered by country instead of category.
NEWSDATA_CATEGORY_PARAMS: Dict[str, Dict[str, str]] = {
    "top": {},
    "world": {"category": "world"},
    "india": {"country": "in"},
    "technology": {"category": "technology"},
    "business": {"category": "business"},
    "science": {"category": "science"},
}

VALID_CATEGORIES = {"top", "world", "india", "technology", "business", "science", "ai", "sports"}

HTTP_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
USER_AGENT = "Jarvis/2.2 News Engine"

# In-process cache: {category: (monotonic_timestamp, NewsResponse)}
_cache: Dict[str, Tuple[float, NewsResponse]] = {}
_lock = asyncio.Lock()


def _strip_html(text: Optional[str]) -> str:
    """Remove HTML tags and collapse whitespace."""
    cleaned = re.sub(r"<[^>]+>", " ", text or "")
    return " ".join(cleaned.split())


def _dedupe(items: List[NewsItem]) -> List[NewsItem]:
    """Drop headlines that are duplicates (same normalized title) of an earlier item."""
    seen: set[str] = set()
    deduped: List[NewsItem] = []
    for item in items:
        key = item.title.strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def _build_narration(items: List[NewsItem], category: str) -> str:
    """Build a Jarvis-style natural narration of the headlines (never dumps raw JSON)."""
    if not items:
        return f"I couldn't find any {category} news right now. Please try again shortly."
    label = category.replace("_", " ").title()
    lines = [f"Here are the top {label} headlines:\n"]
    for i, item in enumerate(items, 1):
        lines.append(f"{i}. {item.title}")
    return "\n".join(lines)


def _extract_source_name(article: Dict[str, Any], fallback: str) -> str:
    """NewsData.io has used a few different shapes for the source field over time; handle them all."""
    source_obj = article.get("source")
    if isinstance(source_obj, dict) and source_obj.get("name"):
        return source_obj["name"]
    return article.get("source_name") or article.get("source_id") or fallback


class NewsService:
    """Fetches, caches, and narrates news headlines from multiple upstream sources."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=6),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    async def _http_get(self, url: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """Shared HTTP helper: async, bounded timeout, up to 3 attempts with backoff."""
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(url, params=params, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
            return response

    async def _fetch_rss(self, url: str, category: str) -> List[NewsItem]:
        """Fetch and parse an RSS feed (used for TechCrunch AI and ESPN)."""
        response = await self._http_get(url)
        feed = feedparser.parse(response.text)
        items: List[NewsItem] = []
        for entry in feed.entries[: settings.news_max_headlines]:
            summary = _strip_html(entry.get("summary") or entry.get("description"))[:300]
            items.append(
                NewsItem(
                    title=entry.get("title", "No title"),
                    summary=summary or "No summary available.",
                    source=feed.feed.get("title") or category.title(),
                    url=entry.get("link", ""),
                    published=entry.get("published"),
                )
            )
        return items

    async def _fetch_newsdata(self, category: str, extra_params: Optional[Dict[str, str]] = None) -> List[NewsItem]:
        """Fetch and parse headlines from the NewsData.io API."""
        if not settings.newsdata_api_key:
            raise NewsServiceError(
                "NewsData.io API key is not configured. Set NEWSDATA_API_KEY in the backend .env."
            )

        params: Dict[str, str] = {"apikey": settings.newsdata_api_key, "language": "en"}
        params.update(extra_params or {})

        response = await self._http_get(NEWSDATA_BASE_URL, params=params)

        try:
            payload = response.json()
        except ValueError as exc:
            raise NewsServiceError(f"NewsData.io returned a non-JSON response: {exc}") from exc

        if payload.get("status") not in ("success", "ok"):
            message = payload.get("message") or payload.get("results") or "unknown error"
            raise NewsServiceError(f"NewsData.io returned an error: {message}")

        articles = payload.get("results") or payload.get("articles") or []
        items: List[NewsItem] = []
        for article in articles[: settings.news_max_headlines]:
            summary = _strip_html(article.get("description") or article.get("content"))[:300]
            items.append(
                NewsItem(
                    title=article.get("title") or "No title",
                    summary=summary or "No summary available.",
                    source=_extract_source_name(article, fallback="NewsData.io"),
                    url=article.get("link") or article.get("url") or "",
                    published=article.get("pubDate") or article.get("publishedAt"),
                )
            )
        return items

    async def _fetch_category(self, category: str) -> List[NewsItem]:
        """Dispatch to the correct upstream source for a given category."""
        if category == "sports":
            return await self._fetch_rss(settings.espn_rss_url, category)

        if category == "ai":
            try:
                items = await self._fetch_rss(TECHCRUNCH_AI_RSS, category)
                if items:
                    return items
                logger.warning("TechCrunch AI feed returned zero items; falling back to NewsData.io")
            except Exception as exc:  # noqa: BLE001 - any TechCrunch failure triggers fallback
                logger.warning("TechCrunch AI feed failed (%s); falling back to NewsData.io", exc)
            return await self._fetch_newsdata(category, {"q": "Artificial Intelligence"})

        params = NEWSDATA_CATEGORY_PARAMS.get(category, {})
        return await self._fetch_newsdata(category, params)

    async def get_news(self, category: str = "top") -> NewsResponse:
        """Return cached-or-fresh, de-duplicated, narrated news for the given category."""
        category = (category or "top").lower()
        if category not in VALID_CATEGORIES:
            category = "top"

        async with _lock:
            cached = _cache.get(category)
            if cached and (time.monotonic() - cached[0]) < settings.news_cache_seconds:
                logger.info("News cache hit for '%s'", category)
                return cached[1]

        try:
            items = await self._fetch_category(category)
        except Exception as exc:  # noqa: BLE001 - convert any upstream failure into a typed error or stale-cache fallback
            logger.error("News fetch failed for category '%s': %s", category, exc)
            if cached:
                logger.warning("Serving stale cached news for '%s' after fetch failure", category)
                return cached[1]
            raise NewsServiceError(f"Failed to fetch {category} news: {exc}") from exc

        items = _dedupe(items)
        narration = _build_narration(items, category)
        response = NewsResponse(
            category=category,
            items=items,
            summary=narration,
            fetched_at=datetime.utcnow(),
        )

        async with _lock:
            _cache[category] = (time.monotonic(), response)

        logger.info("Fetched %d de-duplicated news items for category '%s'", len(items), category)
        return response


news_service = NewsService()
