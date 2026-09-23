"""Outfit recommendation engine.

Responsibilities:
- Select ONLY clean, eligible wardrobe items as candidates.
- Pre-filter by weather bucket and occasion to give the LLM strong signal.
- Ask Groq for outfits, then STRICTLY validate every returned item id against
  the candidate pool (anti-hallucination guarantee).
- Fall back to a deterministic rule-based builder when Groq is unavailable or
  returns unusable output.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.constants import CLEAN_STATUS
from app.models import User, WardrobeItem
from app.schemas.outfit import Outfit, OutfitPiece
from app.services import groq_service

logger = logging.getLogger(__name__)

# Categories that we treat as each outfit slot.
UPPER_CATS = {"Upper", "Ethnic"}
LOWER_CATS = {"Lower"}
SHOE_CATS = {"Shoes"}
OUTER_CATS = {"Outerwear"}
ACCESSORY_CATS = {"Accessories"}


def _item_to_dict(item: WardrobeItem) -> dict:
    return {
        "item_id": item.id,
        "name": item.name,
        "brand": item.brand,
        "category": item.category,
        "subcategory": item.subcategory,
        "primary_color": item.primary_color,
        "secondary_color": item.secondary_color,
        "pattern": item.pattern,
        "material": item.material,
        "fit": item.fit,
        "season": item.season or [],
        "weather": item.weather or [],
        "occasion": item.occasion or [],
        "wear_frequency": item.wear_frequency,
        "favorite": item.favorite,
        "image_url": item.image_url,
    }


def _to_piece(item: WardrobeItem) -> OutfitPiece:
    return OutfitPiece(
        item_id=item.id,
        name=item.name,
        category=item.category,
        subcategory=item.subcategory,
        primary_color=item.primary_color,
        image_url=item.image_url,
        display_image_url=item.display_image_url,
    )


def get_clean_items(items: list[WardrobeItem]) -> list[WardrobeItem]:
    """Only CLEAN items are eligible (PRD rule)."""
    return [i for i in items if (i.laundry_status or "").strip() == CLEAN_STATUS]


def _matches_weather(item: WardrobeItem, bucket: str | None) -> bool:
    if not bucket or bucket == "Mild":
        return True
    tags = item.weather or []
    if not tags:
        return True  # untagged items are considered flexible
    return bucket in tags


def _matches_occasion(item: WardrobeItem, occasion: str | None) -> bool:
    if not occasion:
        return True
    tags = item.occasion or []
    if not tags:
        return True
    return occasion in tags


def build_candidates(
    items: list[WardrobeItem], bucket: str | None, occasion: str | None
) -> list[WardrobeItem]:
    """Clean items filtered by weather + occasion (soft filters)."""
    clean = get_clean_items(items)
    filtered = [
        i
        for i in clean
        if _matches_weather(i, bucket) and _matches_occasion(i, occasion)
    ]
    # If filtering is too aggressive and empties a slot, relax to all clean items.
    if not any(i.category in UPPER_CATS for i in filtered) or not any(
        i.category in LOWER_CATS for i in filtered
    ):
        return clean
    return filtered


def build_user_context(
    user: User | None,
    weather: dict | None,
    request_ctx: dict,
) -> dict:
    profile = {}
    if user:
        profile = {
            "name": user.name,
            "gender": user.gender,
            "body_type": user.body_type,
            "skin_tone": user.skin_tone,
            "undertone": user.undertone,
            "hair_color": user.hair_color,
            "preferred_fit": user.preferred_fit,
            "style": user.style or [],
            "favorite_colors": user.favorite_colors or [],
            "disliked_colors": user.disliked_colors or [],
        }
    return {
        "weather": weather or {},
        "occasion": request_ctx.get("occasion"),
        "time_of_day": request_ctx.get("time_of_day"),
        "dress_code": request_ctx.get("dress_code"),
        "color_preference": request_ctx.get("color_preference"),
        "comfort_vs_style": request_ctx.get("comfort_vs_style"),
        "user_profile": profile,
    }


def _validate_and_resolve(
    raw_outfits: list[dict], by_id: dict[int, WardrobeItem]
) -> list[Outfit]:
    """Convert raw LLM outfits into validated Outfit objects.

    Any item id not present in the candidate pool is dropped, guaranteeing the
    AI can never introduce clothing the user does not own.
    """
    resolved: list[Outfit] = []
    for raw in raw_outfits:
        def pick(key: str) -> OutfitPiece | None:
            val = raw.get(key)
            if isinstance(val, int) and val in by_id:
                return _to_piece(by_id[val])
            return None

        accessories = []
        for aid in raw.get("accessory_ids", []) or []:
            if isinstance(aid, int) and aid in by_id:
                accessories.append(_to_piece(by_id[aid]))

        outfit = Outfit(
            upper=pick("upper_id"),
            lower=pick("lower_id"),
            shoes=pick("shoes_id"),
            outerwear=pick("outerwear_id"),
            accessories=accessories,
            reasoning=str(raw.get("reasoning", "")),
            color_explanation=str(raw.get("color_explanation", "")),
            weather_suitability=str(raw.get("weather_suitability", "")),
            occasion_suitability=str(raw.get("occasion_suitability", "")),
            styling_tips=str(raw.get("styling_tips", "")),
            confidence_score=int(raw.get("confidence_score", 0) or 0),
        )
        # Require at least an upper OR lower to be a meaningful outfit.
        if outfit.upper or outfit.lower:
            resolved.append(outfit)
    return resolved


def _rule_based(
    candidates: list[WardrobeItem], count: int, favorite_item_id: int | None
) -> list[Outfit]:
    """Deterministic fallback: pair items across slots, preferring favorites
    and frequently-worn pieces. Ensures each outfit is distinct."""
    freq_rank = {"Daily": 3, "Often": 2, "Sometimes": 1, "Rarely": 0}

    def sort_key(i: WardrobeItem):
        return (
            0 if favorite_item_id and i.id == favorite_item_id else 1,
            0 if i.favorite else 1,
            -freq_rank.get(i.wear_frequency or "", 0),
        )

    uppers = sorted([i for i in candidates if i.category in UPPER_CATS], key=sort_key)
    lowers = sorted([i for i in candidates if i.category in LOWER_CATS], key=sort_key)
    shoes = sorted([i for i in candidates if i.category in SHOE_CATS], key=sort_key)
    outers = sorted([i for i in candidates if i.category in OUTER_CATS], key=sort_key)
    accs = sorted([i for i in candidates if i.category in ACCESSORY_CATS], key=sort_key)

    outfits: list[Outfit] = []
    for n in range(count):
        upper = uppers[n % len(uppers)] if uppers else None
        lower = lowers[n % len(lowers)] if lowers else None
        shoe = shoes[n % len(shoes)] if shoes else None
        outer = outers[n] if n < len(outers) else None
        acc = [accs[n]] if n < len(accs) else (accs[:1] if accs else [])

        if not upper and not lower:
            break

        parts = [p.primary_color for p in [upper, lower, shoe] if p and p.primary_color]
        color_txt = (
            f"Pairs {', '.join(parts)} for a balanced look."
            if parts
            else "Neutral, easy-to-match pairing."
        )
        outfits.append(
            Outfit(
                upper=_to_piece(upper) if upper else None,
                lower=_to_piece(lower) if lower else None,
                shoes=_to_piece(shoe) if shoe else None,
                outerwear=_to_piece(outer) if outer else None,
                accessories=[_to_piece(a) for a in acc],
                reasoning="Selected from your clean wardrobe based on availability, "
                "favorites and how often you wear each piece.",
                color_explanation=color_txt,
                weather_suitability="Chosen from items tagged for the current weather "
                "where available.",
                occasion_suitability="Matched to the selected occasion where tags "
                "were available.",
                styling_tips="Tuck or layer to taste; keep accessories minimal for a "
                "clean silhouette.",
                confidence_score=70 - n * 5,
            )
        )
    return outfits


def generate(
    user: User | None,
    items: list[WardrobeItem],
    weather: dict | None,
    request_ctx: dict,
) -> tuple[list[Outfit], bool, str | None]:
    """Main entry point. Returns (outfits, used_ai, note)."""
    count = settings.outfit_count
    bucket = (weather or {}).get("bucket")
    occasion = request_ctx.get("occasion")

    candidates = build_candidates(items, bucket, occasion)
    if not candidates:
        return [], False, "No clean wardrobe items available. Add items or mark some as Clean."

    by_id = {i.id: i for i in candidates}
    context = build_user_context(user, weather, request_ctx)

    # Try Groq first (if configured).
    ai_note: str | None = None
    if settings.groq_enabled:
        try:
            candidate_dicts = [_item_to_dict(i) for i in candidates]
            raw = groq_service.generate_outfits(context, candidate_dicts, count)
            resolved = _validate_and_resolve(raw, by_id)
            if resolved:
                return resolved[:count], True, None
            logger.warning("Groq returned no usable outfits; using rule-based fallback.")
            ai_note = (
                "AI returned no usable outfits (none referenced your items) — "
                "showing rule-based picks."
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Groq call failed (%s); using rule-based fallback.", exc)
            ai_note = (
                f"AI unavailable — using rule-based stylist. "
                f"Reason: {type(exc).__name__}: {exc}. "
                f"(Check GROQ_MODEL='{settings.groq_model}' is a current Groq model.)"
            )
    else:
        ai_note = "Groq API key not configured — using built-in rule-based stylist."

    return (
        _rule_based(candidates, count, request_ctx.get("favorite_item_id")),
        False,
        ai_note,
    )
