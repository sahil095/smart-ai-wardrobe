"""A single "I wore this" event."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class WearEvent(Base):
    __tablename__ = "wear_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    item_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    snapshot: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="generated")

    worn_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )
