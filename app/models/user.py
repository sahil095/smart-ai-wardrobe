"""User (wardrobe owner) ORM model."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username", name="uq_users_username"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str | None] = mapped_column(String(80), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(120), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(40), nullable=True)
    height: Mapped[str | None] = mapped_column(String(40), nullable=True)
    weight: Mapped[str | None] = mapped_column(String(40), nullable=True)
    body_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    skin_tone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    undertone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    hair_color: Mapped[str | None] = mapped_column(String(40), nullable=True)
    eye_color: Mapped[str | None] = mapped_column(String(40), nullable=True)
    preferred_fit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Multi-select stored as JSON list
    style: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    favorite_colors: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    disliked_colors: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    default_shoe_size: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Stated taste, e.g. [{"text", "source", "created_at"}]. Cap 20 in the service.
    style_memories: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    items: Mapped[list["WardrobeItem"]] = relationship(  # noqa: F821
        back_populates="owner", cascade="all, delete-orphan"
    )
