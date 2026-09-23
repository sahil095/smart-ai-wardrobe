"""Category-dependent attribute schema (Phase 1).

Stores an AI-generated (or builtin) list of filterable attributes per
(category, subcategory), cached so we don't call the LLM repeatedly. Each row's
`schema` is a JSON list of field definitions:
    [{"key": "sole_type", "label": "Sole Type", "type": "select",
      "options": ["Rubber", "EVA", "Leather"]}, ...]
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class AttributeSchema(Base):
    __tablename__ = "attribute_schemas"
    __table_args__ = (
        UniqueConstraint("category", "subcategory", name="uq_attr_cat_sub"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    # Empty string denotes a category-level schema (avoids NULL-uniqueness issues)
    subcategory: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    schema: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="ai")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
