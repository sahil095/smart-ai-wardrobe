"""Cached style-idea photos for one search query."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class InspirationCache(Base):
    __tablename__ = "inspiration_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    query_key: Mapped[str] = mapped_column(String(240), unique=True, nullable=False)
    photos: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    # "pexels" when the row came from Pexels. Empty on older rows.
    provider: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
