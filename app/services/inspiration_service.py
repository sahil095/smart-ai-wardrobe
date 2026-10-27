"""Style inspiration: similar outfit photos, never shopping."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from urllib.parse import quote, quote_plus

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import InspirationCache, WardrobeItem

logger = logging.getLogger(__name__)

PEXELS_SEARCH = "https://api.pexels.com/v1/search"
PIXABAY_SEARCH = "https://pixabay.com/api/"


def normalize_query(query: str) -> str:
    return " ".join((query or "").lower().split())[:180]


def style_query(query: str) -> str:
    """The search both Pixabay and Pinterest should use, ending in 'outfit'."""
    key = normalize_query(query)
    if not key:
        return ""
    if not re.search(r"\boutfit\b", key):
        key = f"{key} outfit"
    return key[:180]


def display_label(query: str) -> str:
    """Header text: the search words without the trailing 'outfit'."""
    key = style_query(query)
    if key.endswith(" outfit"):
        key = key[: -len(" outfit")]
    return key or "this piece"


def query_for_item(item: WardrobeItem) -> str:
    """Color + garment type + outfit, so results are styled looks not product shots."""
    color = (item.primary_color or "").strip()
    kind = (item.subcategory or "").strip() or (item.category or "").strip()
    if not kind:
        kind = (item.name or "clothes").strip()
    parts = [p for p in (color, kind, "outfit") if p]
    return normalize_query(" ".join(parts))


def pinterest_url(query: str) -> str:
    q = quote_plus(style_query(query) or "outfit ideas")
    return f"https://www.pinterest.com/search/pins/?q={q}"


def pixabay_url(query: str) -> str:
    q = quote(style_query(query) or "outfit ideas")
    return f"https://pixabay.com/images/search/{q}/"


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


def _active_provider() -> str | None:
    """Pixabay wins when its key is set. Pexels remains available after that."""
    if settings.pixabay_enabled:
        return "pixabay"
    if settings.pexels_enabled:
        return "pexels"
    return None


def _photo_pixabay(raw: dict) -> dict | None:
    src = raw.get("webformatURL") or raw.get("largeImageURL") or raw.get("previewURL")
    if not src:
        return None
    user = str(raw.get("user") or "").strip()
    user_id = raw.get("user_id")
    profile = ""
    if user and user_id:
        profile = f"https://pixabay.com/users/{quote(user, safe='')}-{user_id}/"
    alt = str(raw.get("tags") or "Outfit inspiration").strip() or "Outfit inspiration"
    return {
        "image_url": src,
        "alt": alt[:180],
        "photographer": user,
        "photographer_url": profile,
        "source_url": raw.get("pageURL") or "https://pixabay.com/",
    }


async def _fetch_pixabay(query: str) -> list[dict]:
    if not settings.pixabay_enabled:
        return []
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            PIXABAY_SEARCH,
            params={
                "key": settings.pixabay_api_key,
                "q": query[:100],
                "image_type": "photo",
                "safesearch": "true",
                "per_page": 6,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    photos = []
    for raw in data.get("hits") or []:
        photo = _photo_pixabay(raw)
        if photo:
            photos.append(photo)
    return photos[:6]


async def _fetch_pexels(query: str) -> list[dict]:
    if not settings.pexels_enabled:
        return []
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            PEXELS_SEARCH,
            params={"query": query, "per_page": 6, "orientation": "portrait"},
            headers={"Authorization": settings.pexels_api_key},
        )
        resp.raise_for_status()
        data = resp.json()
    photos = []
    for raw in data.get("photos") or []:
        photo = _photo(raw)
        if photo:
            photos.append(photo)
    return photos[:6]


async def search(db: Session, query: str, commit: bool = True) -> dict:
    key = style_query(query)
    pin = pinterest_url(key or "outfit ideas")
    pix = pixabay_url(key or "outfit ideas")
    if not key:
        return {
            "query": "",
            "photos": [],
            "pinterest_url": pin,
            "pixabay_url": pix,
            "cached": False,
            "note": "Add a color or garment type to search.",
        }

    provider = _active_provider()
    now = datetime.utcnow()
    ttl = timedelta(hours=max(1, settings.gap_cache_hours))
    cached = db.scalar(
        select(InspirationCache).where(InspirationCache.query_key == key)
    )
    cached_provider = (cached.provider if cached else None) or "pexels"
    fresh = bool(cached and cached.created_at and (now - cached.created_at) < ttl)
    if fresh and provider and cached_provider == provider:
        return {
            "query": key,
            "photos": (cached.photos or [])[:6],
            "pinterest_url": pin,
            "pixabay_url": pix,
            "cached": True,
            "provider": provider,
            "note": None if cached.photos else "No similar photos for that search. Try Pinterest.",
        }

    photos: list[dict] = []
    note = None
    if provider == "pixabay":
        try:
            photos = await _fetch_pixabay(key)
            if not photos:
                note = "No similar photos for that search. Try Pinterest."
        except Exception as exc:  # noqa: BLE001
            # Do not log the exception text: it can include the request URL and key.
            logger.warning("Pixabay search failed (%s)", exc.__class__.__name__)
            note = "Inspiration search is unavailable right now. Pinterest still works."
    elif provider == "pexels":
        try:
            photos = await _fetch_pexels(key)
            if not photos:
                note = "No similar photos for that search. Try Pinterest."
        except Exception as exc:  # noqa: BLE001
            logger.warning("Pexels search failed: %s", exc)
            note = "Inspiration search is unavailable right now. Pinterest still works."
    else:
        note = _no_key_note()

    if provider and photos:
        if cached:
            cached.photos = photos
            cached.provider = provider
            cached.created_at = now
        else:
            db.add(InspirationCache(
                query_key=key, photos=photos, provider=provider, created_at=now,
            ))
        if commit:
            db.commit()
        else:
            db.flush()

    return {
        "query": key,
        "photos": photos[:6],
        "pinterest_url": pin,
        "pixabay_url": pix,
        "cached": False,
        "provider": provider,
        "note": note,
    }


def _no_key_note() -> str:
    return "Add PIXABAY_API_KEY for in-app photos. Pinterest search still works."
