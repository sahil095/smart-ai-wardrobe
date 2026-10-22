"""Style inspiration: similar outfit photos, never shopping."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import InspirationCache, WardrobeItem

logger = logging.getLogger(__name__)

PEXELS_SEARCH = "https://api.pexels.com/v1/search"


def normalize_query(query: str) -> str:
    return " ".join((query or "").lower().split())[:180]


def query_for_item(item: WardrobeItem) -> str:
    """Color + garment type + outfit, so results are styled looks not product shots."""
    color = (item.primary_color or "").strip()
    kind = (item.subcategory or "").strip() or (item.category or "").strip()
    if not kind:
        kind = (item.name or "clothes").strip()
    parts = [p for p in (color, kind, "outfit") if p]
    return normalize_query(" ".join(parts))


def pinterest_url(query: str) -> str:
    q = quote_plus(normalize_query(query) or "outfit ideas")
    return f"https://www.pinterest.com/search/pins/?q={q}"


def _photo(raw: dict) -> dict | None:
    src = (raw.get("src") or {}).get("medium") or (raw.get("src") or {}).get("large")
    if not src:
        return None
    return {
        "image_url": src,
        "alt": (raw.get("alt") or "Outfit inspiration")[:180],
        "photographer": raw.get("photographer") or "",
        "photographer_url": raw.get("photographer_url") or "",
        "source_url": raw.get("url") or "https://www.pexels.com",
    }


async def _fetch_pexels(query: str) -> list[dict]:
    if not settings.pexels_enabled:
        return []
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            PEXELS_SEARCH,
            params={"query": query, "per_page": 8, "orientation": "portrait"},
            headers={"Authorization": settings.pexels_api_key},
        )
        resp.raise_for_status()
        data = resp.json()
    photos = []
    for raw in data.get("photos") or []:
        photo = _photo(raw)
        if photo:
            photos.append(photo)
    return photos[:8]


async def search(db: Session, query: str, commit: bool = True) -> dict:
    key = normalize_query(query)
    pin = pinterest_url(key or "outfit ideas")
    if not key:
        return {
            "query": "",
            "photos": [],
            "pinterest_url": pin,
            "cached": False,
            "note": "Add a color or garment type to search.",
        }

    now = datetime.utcnow()
    ttl = timedelta(hours=max(1, settings.gap_cache_hours))
    cached = db.scalar(
        select(InspirationCache).where(InspirationCache.query_key == key)
    )
    if cached and cached.created_at and (now - cached.created_at) < ttl:
        return {
            "query": key,
            "photos": cached.photos or [],
            "pinterest_url": pin,
            "cached": True,
            "note": None if (cached.photos or settings.pexels_enabled) else _no_key_note(),
        }

    photos: list[dict] = []
    note = None
    if settings.pexels_enabled:
        try:
            photos = await _fetch_pexels(key)
            if not photos:
                note = "No similar photos for that search. Try Pinterest."
        except Exception as exc:  # noqa: BLE001
            logger.warning("Pexels search failed: %s", exc)
            note = "Inspiration search is unavailable right now. Pinterest still works."
    else:
        note = _no_key_note()

    if settings.pexels_enabled and photos:
        if cached:
            cached.photos = photos
            cached.created_at = now
        else:
            db.add(InspirationCache(query_key=key, photos=photos, created_at=now))
        if commit:
            db.commit()
        else:
            db.flush()

    return {
        "query": key,
        "photos": photos,
        "pinterest_url": pin,
        "cached": False,
        "note": note,
    }


def _no_key_note() -> str:
    return "Add PEXELS_API_KEY for in-app photos. Pinterest search still works."
