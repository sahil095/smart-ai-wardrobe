"""Wardrobe gap analysis: census + Groq, with deterministic fallback."""
from __future__ import annotations

import hashlib
import json
import logging
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import WardrobeGapRun, WardrobeItem
from app.services import groq_service

logger = logging.getLogger(__name__)

LIGHT_WORDS = {
    "white", "off-white", "ivory", "cream", "beige", "khaki", "tan",
    "light", "light blue", "light grey", "light gray", "stone", "sand",
}


def build_census(items: list[WardrobeItem]) -> dict:
    cats: Counter = Counter()
    subs: Counter = Counter()
    colors: Counter = Counter()
    seasons: Counter = Counter()
    occasions: Counter = Counter()
    weather: Counter = Counter()
    colors_by_cat: dict[str, Counter] = {}
    clean = 0
    for it in items:
        cat = it.category or "Unknown"
        cats[cat] += 1
        if it.subcategory:
            subs[it.subcategory] += 1
        if it.primary_color:
            color = it.primary_color.strip().lower()
            colors[color] += 1
            colors_by_cat.setdefault(cat, Counter())[color] += 1
        for s in it.season or []:
            seasons[s] += 1
        for o in it.occasion or []:
            occasions[o] += 1
        for w in it.weather or []:
            weather[w] += 1
        if (it.laundry_status or "") == "Clean":
            clean += 1
    return {
        "total": len(items),
        "clean": clean,
        "categories": dict(cats),
        "subcategories": dict(subs),
        "colors": dict(colors),
        "colors_by_category": {k: dict(v) for k, v in colors_by_cat.items()},
        "seasons": dict(seasons),
        "occasions": dict(occasions),
        "weather": dict(weather),
    }


def census_hash(census: dict) -> str:
    blob = json.dumps(census, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _is_light(color: str) -> bool:
    c = (color or "").lower()
    return any(w in c for w in LIGHT_WORDS)


def rule_cards(census: dict) -> list[dict]:
    """Cheap, testable gaps when Groq is unavailable."""
    cards: list[dict] = []
    cats = census.get("categories") or {}
    colors = census.get("colors") or {}
    occasions = census.get("occasions") or {}
    weather = census.get("weather") or {}
    seasons = census.get("seasons") or {}

    if cats.get("Shoes", 0) < 1:
        cards.append({
            "title": "No shoes logged",
            "why": "Outfits need shoes. Your census has none.",
            "suggestion": "Add at least one pair of everyday sneakers or loafers.",
            "severity": "high",
        })
    if cats.get("Upper", 0) + cats.get("Ethnic", 0) < 1:
        cards.append({
            "title": "No tops logged",
            "why": "There are no Upper/Ethnic items to build looks around.",
            "suggestion": "Add a few everyday tops (tee, shirt, or hoodie).",
            "severity": "high",
        })
    if cats.get("Lower", 0) < 1:
        cards.append({
            "title": "No bottoms logged",
            "why": "There are no Lower items in the wardrobe.",
            "suggestion": "Add jeans or chinos so outfits can be completed.",
            "severity": "high",
        })
    elif cats.get("Lower", 0) < 2:
        cards.append({
            "title": "Only one pair of bottoms",
            "why": f"You have {cats.get('Lower')} lower item(s).",
            "suggestion": "A second pair in a different color unlocks more outfits.",
            "severity": "medium",
        })

    lower_colors = (census.get("colors_by_category") or {}).get("Lower") or {}
    if cats.get("Lower", 0) >= 1 and lower_colors and not any(_is_light(c) for c in lower_colors):
        cards.append({
            "title": "No light summer bottoms",
            "why": "Your bottoms are tagged with darker colors only — few summer or office mixes.",
            "suggestion": "Add light chinos, linen pants, or another pale bottom.",
            "severity": "medium",
        })
    elif cats.get("Lower", 0) >= 1 and not lower_colors and colors and not any(_is_light(c) for c in colors):
        cards.append({
            "title": "No light colors tagged",
            "why": "Every tagged primary color is mid/dark — hard to build summer or office looks.",
            "suggestion": "Add a light bottom or a white/cream top (and tag the color).",
            "severity": "medium",
        })

    if weather.get("Rain", 0) < 1:
        cards.append({
            "title": "Nothing tagged for rain",
            "why": "No items list Rain under weather suitability.",
            "suggestion": "Add or tag a rain jacket / water-resistant layer.",
            "severity": "medium",
        })
    if occasions.get("Office", 0) < 1 and occasions.get("Interview", 0) < 1:
        cards.append({
            "title": "No office-tagged pieces",
            "why": "Nothing is tagged for Office or Interview.",
            "suggestion": "Tag a shirt, chinos, or formal shoes for Office — or add one.",
            "severity": "medium",
        })
    if seasons.get("Summer", 0) < 1 and seasons.get("All Season", 0) < 2:
        cards.append({
            "title": "Thin summer coverage",
            "why": "Few items are tagged Summer or All Season.",
            "suggestion": "Add or tag a light, breathable bottom or short-sleeve top.",
            "severity": "medium",
        })
    return cards[:6]


def _valid_card(card: dict) -> bool:
    return bool(card.get("title") and (card.get("why") or card.get("suggestion")))


def _contradicts_census(card: dict, census: dict) -> bool:
    """Drop Groq cards that claim a slot is missing when the census has it."""
    text = f"{card.get('title', '')} {card.get('why', '')}".lower()
    cats = census.get("categories") or {}
    checks = (
        (("shoe", "sneaker", "loafer"), "Shoes"),
        (("bottom", "trouser", "jean", "chino"), "Lower"),
        (("top", "shirt", "tee", "hoodie"), "Upper"),
        (("outerwear", "jacket", "coat"), "Outerwear"),
    )
    missing_words = ("no ", "missing ", "don't have ", "do not have ", "0 ")
    for words, cat in checks:
        claimed_absent = any(mw + w in text for mw in missing_words for w in words)
        if claimed_absent and cats.get(cat, 0) > 0:
            return True
    return False


def analyze(db: Session, user_id: int, items: list[WardrobeItem], refresh: bool = False) -> dict:
    census = build_census(items)
    digest = census_hash(census)
    now = datetime.utcnow()
    ttl = timedelta(hours=max(1, settings.gap_cache_hours))

    if not refresh:
        cached = db.scalar(
            select(WardrobeGapRun)
            .where(WardrobeGapRun.user_id == user_id)
            .order_by(WardrobeGapRun.created_at.desc())
        )
        if (
            cached
            and cached.census_hash == digest
            and cached.created_at
            and (now - cached.created_at) < ttl
        ):
            return {
                "cards": cached.cards or [],
                "used_ai": bool(cached.used_ai),
                "cached": True,
                "census": census,
            }

    if census["total"] == 0:
        return {"cards": [], "used_ai": False, "cached": False, "census": census}

    cards: list[dict] = []
    used_ai = False
    if settings.groq_enabled:
        try:
            raw = groq_service.generate_gap_cards(census)
            cards = [c for c in raw if _valid_card(c) and not _contradicts_census(c, census)]
            used_ai = bool(cards)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gap Groq call failed: %s", exc)

    if not cards:
        cards = rule_cards(census)

    row = WardrobeGapRun(
        user_id=user_id,
        census_hash=digest,
        cards=cards,
        used_ai=1 if used_ai else 0,
        created_at=now,
    )
    db.add(row)
    db.commit()
    return {"cards": cards, "used_ai": used_ai, "cached": False, "census": census}
