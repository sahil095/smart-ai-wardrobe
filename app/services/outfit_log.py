"""Helpers for saved outfits and wear events."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SavedOutfit, WardrobeItem, WearEvent


def normalize_ids(item_ids: list | None) -> list[int]:
    ids: list[int] = []
    for raw in item_ids or []:
        try:
            n = int(raw)
        except (TypeError, ValueError):
            continue
        if n > 0:
            ids.append(n)
    return sorted(set(ids))


def fingerprint(item_ids: list[int]) -> str:
    return ",".join(str(i) for i in normalize_ids(item_ids))


def ids_from_outfit_dict(outfit: dict | None) -> list[int]:
    """Extract item ids from a generated Outfit-shaped dict."""
    if not outfit:
        return []
    ids: list[int] = []
    for key in ("upper", "lower", "shoes", "outerwear"):
        piece = outfit.get(key)
        if isinstance(piece, dict) and piece.get("item_id"):
            ids.append(piece["item_id"])
    for piece in outfit.get("accessories") or []:
        if isinstance(piece, dict) and piece.get("item_id"):
            ids.append(piece["item_id"])
    return normalize_ids(ids)


def snapshot_items(db: Session, user_id: int, item_ids: list[int]) -> list[dict]:
    """Resolve owned items into display snapshots."""
    ids = normalize_ids(item_ids)
    if not ids:
        return []
    rows = db.scalars(
        select(WardrobeItem).where(
            WardrobeItem.user_id == user_id, WardrobeItem.id.in_(ids)
        )
    ).all()
    by_id = {r.id: r for r in rows}
    snaps = []
    for iid in ids:
        it = by_id.get(iid)
        if not it:
            continue
        snaps.append(
            {
                "item_id": it.id,
                "name": it.name,
                "category": it.category,
                "subcategory": it.subcategory,
                "primary_color": it.primary_color,
                "image_url": it.image_url,
                "display_image_url": it.display_image_url,
                "laundry_status": it.laundry_status,
            }
        )
    return snaps


def recently_worn_item_ids(db: Session, user_id: int, days: int = 7) -> list[int]:
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    rows = db.scalars(
        select(WearEvent).where(
            WearEvent.user_id == user_id, WearEvent.worn_at >= cutoff
        )
    ).all()
    ids: list[int] = []
    for row in rows:
        ids.extend(normalize_ids(row.item_ids))
    return sorted(set(ids))


def saved_fingerprints(db: Session, user_id: int) -> list[list[int]]:
    rows = db.scalars(
        select(SavedOutfit).where(SavedOutfit.user_id == user_id)
    ).all()
    return [normalize_ids(r.item_ids) for r in rows]
