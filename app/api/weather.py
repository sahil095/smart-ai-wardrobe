"""Weather + geocoding API (Open-Meteo)."""
import httpx
from fastapi import APIRouter, HTTPException

from app.services import weather_service

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("/current")
async def current_weather(
    latitude: float | None = None,
    longitude: float | None = None,
    city: str | None = None,
):
    """Get current weather by coordinates (auto) or city name (manual override)."""
    try:
        location_name = None
        if latitude is None or longitude is None:
            if not city:
                raise HTTPException(
                    status_code=400,
                    detail="Provide latitude+longitude or a city name.",
                )
            geo = await weather_service.geocode(city)
            if not geo:
                raise HTTPException(status_code=404, detail="City not found.")
            latitude, longitude = geo["latitude"], geo["longitude"]
            location_name = geo["name"]

        return await weather_service.get_current_weather(
            latitude, longitude, location_name
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Weather service error: {exc}"
        ) from exc
