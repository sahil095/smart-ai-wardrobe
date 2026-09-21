"""Pydantic schemas for the outfit generator."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.wardrobe import WardrobeItemOut


class OutfitGenerateRequest(BaseModel):
    user_id: int
    occasion: str | None = None
    time_of_day: str | None = None
    dress_code: str | None = None
    color_preference: str | None = None
    comfort_vs_style: str | None = None  # "Comfort" | "Balanced" | "Style"
    favorite_item_id: int | None = None

    # Weather: either provided coordinates (auto) or a manual override.
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None
    # Manual weather override (skips Open-Meteo lookup when provided)
    manual_temp_c: float | None = None
    manual_condition: str | None = None


class OutfitPiece(BaseModel):
    """A resolved piece within an outfit (linked to a real wardrobe item)."""
    item_id: int
    name: str
    category: str
    subcategory: str | None = None
    primary_color: str | None = None
    image_url: str | None = None


class Outfit(BaseModel):
    upper: OutfitPiece | None = None
    lower: OutfitPiece | None = None
    shoes: OutfitPiece | None = None
    outerwear: OutfitPiece | None = None
    accessories: list[OutfitPiece] = Field(default_factory=list)
    reasoning: str = ""
    color_explanation: str = ""
    weather_suitability: str = ""
    occasion_suitability: str = ""
    styling_tips: str = ""
    confidence_score: int = 0


class WeatherInfo(BaseModel):
    temperature_c: float | None = None
    condition: str | None = None
    location_name: str | None = None
    source: str = "unknown"


class OutfitGenerateResponse(BaseModel):
    weather: WeatherInfo
    outfits: list[Outfit]
    used_ai: bool
    note: str | None = None


class OutfitHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    occasion: str | None = None
    context: dict | None = None
    outfits: list | None = None
    created_at: datetime
