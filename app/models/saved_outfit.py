"""Saved (favorited) outfit — a reusable set of wardrobe item IDs."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class SavedOutfit(Base):
    __tablename__ = "saved_outfits"
    __table_args__ = (
        UniqueConstraint("user_id", "fingerprint", name="uq_saved_user_fingerprint"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Sorted unique item ids, e.g. "3,12,44"
    fingerprint: Mapped[str] = mapped_column(String(240), nullable=False)
    item_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Resolved piece snapshots for display even if tags later change
    snapshot: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    label: Mapped[str | None] = mapped_column(String(150), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
