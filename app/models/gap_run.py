"""Cached wardrobe-gap analysis for a user."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class WardrobeGapRun(Base):
    __tablename__ = "wardrobe_gap_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    census_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    cards: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    used_ai: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
