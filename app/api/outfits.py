"""Outfit generation + history API."""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OutfitHistory, SavedOutfit, User, WardrobeItem, WearEvent
from app.schemas import (
    OutfitGenerateRequest,
    OutfitGenerateResponse,
    OutfitHistoryOut,
    OutfitIdsIn,
    SavedOutfitOut,
    WearEventOut,
    WeatherInfo,
)
from app.services import outfit_engine, outfit_log, weather_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/outfits", tags=["outfits"])


async def _resolve_weather(req: OutfitGenerateRequest) -> dict | None:
    # Manual override wins.
    if req.manual_temp_c is not None or req.manual_condition:
        bucket = weather_service.condition_bucket(
            -1, req.manual_temp_c, None
        )
        # If a manual condition string maps to a bucket keyword, prefer it.
        for kw in ["Snow", "Rain", "Windy", "Cold", "Hot"]:
            if req.manual_condition and kw.lower() in req.manual_condition.lower():
                bucket = kw
        return {
            "temperature_c": req.manual_temp_c,
            "condition": req.manual_condition or bucket,
            "bucket": bucket,
            "location_name": req.location_name,
            "source": "manual",
        }
    if req.latitude is not None and req.longitude is not None:
        try:
            return await weather_service.get_current_weather(
                req.latitude, req.longitude, req.location_name
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Weather lookup failed: %s", exc)
            return None
    if req.location_name:
        try:
            geo = await weather_service.geocode(req.location_name)
            if geo:
                return await weather_service.get_current_weather(
                    geo["latitude"], geo["longitude"], geo["name"]
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Geocode/weather failed: %s", exc)
    return None


@router.post("/generate", response_model=OutfitGenerateResponse)
async def generate_outfits(
    req: OutfitGenerateRequest, db: Session = Depends(get_db)
):
    user = db.get(User, req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    items = db.scalars(
        select(WardrobeItem).where(WardrobeItem.user_id == req.user_id)
    ).all()

    weather = await _resolve_weather(req)

    request_ctx = {
        "occasion": req.occasion,
        "time_of_day": req.time_of_day,
        "dress_code": req.dress_code,
        "color_preference": req.color_preference,
        "comfort_vs_style": req.comfort_vs_style,
        "favorite_item_id": req.favorite_item_id,
        "recently_worn_item_ids": outfit_log.recently_worn_item_ids(db, req.user_id),
        "saved_outfits": outfit_log.saved_fingerprints(db, req.user_id),
    }

    outfits, used_ai, note = outfit_engine.generate(user, items, weather, request_ctx)

    weather_info = WeatherInfo(
        temperature_c=(weather or {}).get("temperature_c"),
        condition=(weather or {}).get("condition"),
        location_name=(weather or {}).get("location_name"),
        source=(weather or {}).get("source", "unknown"),
    )

    # Persist to history (supports the History nav tab).
    if outfits:
        history = OutfitHistory(
            user_id=req.user_id,
            occasion=req.occasion,
            context={**request_ctx, "weather": weather},
            outfits=[o.model_dump() for o in outfits],
        )
        db.add(history)
        db.commit()

    return OutfitGenerateResponse(
        weather=weather_info, outfits=outfits, used_ai=used_ai, note=note
    )


@router.get("/history", response_model=list[OutfitHistoryOut])
def list_history(user_id: int, limit: int = 50, db: Session = Depends(get_db)):
    stmt = (
        select(OutfitHistory)
        .where(OutfitHistory.user_id == user_id)
        .order_by(OutfitHistory.created_at.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()


@router.delete("/history/{history_id}", status_code=204)
def delete_history(history_id: int, db: Session = Depends(get_db)):
    row = db.get(OutfitHistory, history_id)
    if not row:
        raise HTTPException(status_code=404, detail="History entry not found")
    db.delete(row)
    db.commit()


@router.get("/saved", response_model=list[SavedOutfitOut])
def list_saved(user_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(SavedOutfit)
        .where(SavedOutfit.user_id == user_id)
        .order_by(SavedOutfit.created_at.desc())
    ).all()


@router.post("/save", response_model=SavedOutfitOut)
def save_outfit(payload: OutfitIdsIn, db: Session = Depends(get_db)):
    if not db.get(User, payload.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    ids = outfit_log.normalize_ids(payload.item_ids)
    if not ids:
        raise HTTPException(status_code=400, detail="Select at least one item.")
    fp = outfit_log.fingerprint(ids)
    existing = db.scalar(
        select(SavedOutfit).where(
            SavedOutfit.user_id == payload.user_id,
            SavedOutfit.fingerprint == fp,
        )
    )
    if existing:
        return existing
    row = SavedOutfit(
        user_id=payload.user_id,
        item_ids=ids,
        fingerprint=fp,
        snapshot=outfit_log.snapshot_items(db, payload.user_id, ids),
        label=payload.label,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/saved/{saved_id}", status_code=204)
def unsave_outfit(saved_id: int, db: Session = Depends(get_db)):
    row = db.get(SavedOutfit, saved_id)
    if not row:
        raise HTTPException(status_code=404, detail="Saved outfit not found")
    db.delete(row)
    db.commit()


@router.get("/worn", response_model=list[WearEventOut])
def list_worn(user_id: int, limit: int = 50, db: Session = Depends(get_db)):
    return db.scalars(
        select(WearEvent)
        .where(WearEvent.user_id == user_id)
        .order_by(WearEvent.worn_at.desc())
        .limit(limit)
    ).all()


@router.post("/wear", response_model=WearEventOut)
def log_wear(payload: OutfitIdsIn, db: Session = Depends(get_db)):
    if not db.get(User, payload.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    ids = outfit_log.normalize_ids(payload.item_ids)
    if not ids:
        raise HTTPException(status_code=400, detail="Select at least one item.")
    now = datetime.utcnow()
    event = WearEvent(
        user_id=payload.user_id,
        item_ids=ids,
        snapshot=outfit_log.snapshot_items(db, payload.user_id, ids),
        source=payload.source or "generated",
        worn_at=now,
    )
    db.add(event)
    items = db.scalars(
        select(WardrobeItem).where(
            WardrobeItem.user_id == payload.user_id, WardrobeItem.id.in_(ids)
        )
    ).all()
    for it in items:
        it.last_worn_at = now
    db.commit()
    db.refresh(event)
    return event
