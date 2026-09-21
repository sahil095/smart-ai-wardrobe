"""Outfit history ORM model.

Stores generated outfit sessions so the History page (bottom nav) can show
previously generated recommendations. Designed to support the "Future
Features" (recently worn / favorites) without a schema rewrite.
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class OutfitHistory(Base):
    __tablename__ = "outfit_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    occasion: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # Snapshot of the generator inputs (weather, dress code, etc.)
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    # List of generated outfit objects (with resolved item details)
    outfits: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
