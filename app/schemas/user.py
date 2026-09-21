"""Pydantic schemas for User."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    nickname: str | None = None
    age: int | None = Field(default=None, ge=0, le=130)
    gender: str | None = None
    height: str | None = None
    weight: str | None = None
    body_type: str | None = None
    skin_tone: str | None = None
    undertone: str | None = None
    hair_color: str | None = None
    eye_color: str | None = None
    preferred_fit: str | None = None
    style: list[str] = Field(default_factory=list)
    favorite_colors: list[str] = Field(default_factory=list)
    disliked_colors: list[str] = Field(default_factory=list)
    default_shoe_size: str | None = None
    notes: str | None = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    nickname: str | None = None
    age: int | None = Field(default=None, ge=0, le=130)
    gender: str | None = None
    height: str | None = None
    weight: str | None = None
    body_type: str | None = None
    skin_tone: str | None = None
    undertone: str | None = None
    hair_color: str | None = None
    eye_color: str | None = None
    preferred_fit: str | None = None
    style: list[str] | None = None
    favorite_colors: list[str] | None = None
    disliked_colors: list[str] | None = None
    default_shoe_size: str | None = None
    notes: str | None = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
