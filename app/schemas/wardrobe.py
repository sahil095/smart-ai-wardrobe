"""Pydantic schemas for wardrobe items."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WardrobeItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    brand: str | None = None
    category: str = Field(..., min_length=1, max_length=60)
    subcategory: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    pattern: str | None = None
    material: str | None = None
    fit: str | None = None
    size: str | None = None
    season: list[str] = Field(default_factory=list)
    weather: list[str] = Field(default_factory=list)
    occasion: list[str] = Field(default_factory=list)
    sleeve_type: str | None = None
    neck_type: str | None = None
    condition: str | None = None
    wear_frequency: str | None = None
    favorite: bool = False
    laundry_status: str = "Clean"
    image_url: str | None = None
    notes: str | None = None


class WardrobeItemCreate(WardrobeItemBase):
    user_id: int


class WardrobeItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    brand: str | None = None
    category: str | None = None
    subcategory: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    pattern: str | None = None
    material: str | None = None
    fit: str | None = None
    size: str | None = None
    season: list[str] | None = None
    weather: list[str] | None = None
    occasion: list[str] | None = None
    sleeve_type: str | None = None
    neck_type: str | None = None
    condition: str | None = None
    wear_frequency: str | None = None
    favorite: bool | None = None
    laundry_status: str | None = None
    image_url: str | None = None
    notes: str | None = None


class WardrobeItemOut(WardrobeItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
