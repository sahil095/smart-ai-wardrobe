"""Outfit generation + history API."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OutfitHistory, User, WardrobeItem
from app.schemas import (
    OutfitGenerateRequest,
    OutfitGenerateResponse,
    OutfitHistoryOut,
    WeatherInfo,
)
from app.services import outfit_engine, weather_service

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
