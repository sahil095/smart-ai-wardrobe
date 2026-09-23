"""Wardrobe item ORM model."""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class WardrobeItem(Base):
    __tablename__ = "wardrobe_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(60), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(60), nullable=True)
    secondary_color: Mapped[str | None] = mapped_column(String(60), nullable=True)
    pattern: Mapped[str | None] = mapped_column(String(60), nullable=True)
    material: Mapped[str | None] = mapped_column(String(60), nullable=True)
    fit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    size: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # Multi-select fields stored as JSON lists
    season: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    weather: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    occasion: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    sleeve_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    neck_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    condition: Mapped[str | None] = mapped_column(String(40), nullable=True)
    wear_frequency: Mapped[str | None] = mapped_column(String(40), nullable=True)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    laundry_status: Mapped[str] = mapped_column(
        String(40), default="Clean", nullable=False, index=True
    )
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Standardized ("retail PDP") variant + Cloudinary public_id for transforms
    display_image_url: Mapped[str | None] = mapped_column(String(700), nullable=True)
    image_public_id: Mapped[str | None] = mapped_column(String(300), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Category-dependent attributes (Phase 1), e.g. {"sole_type": "Rubber"}
    attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    owner: Mapped["User"] = relationship(back_populates="items")  # noqa: F821
