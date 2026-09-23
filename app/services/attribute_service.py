"""Category-dependent attribute schemas (Phase 1).

Resolution order for a (category, subcategory):
1. DB cache (AttributeSchema table).
2. Groq generation (if configured) -> cached to DB.
3. Builtin fallback from constants (category-level).

Returns a list of field defs: {key, label, type:'select'|'text', options?}.
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import constants
from app.config import settings
from app.models import AttributeSchema
from app.services import groq_service

logger = logging.getLogger(__name__)


def _builtin(category: str) -> list[dict]:
    return list(constants.BUILTIN_ATTRIBUTE_SCHEMAS.get(category, []))


def _get_cached(db: Session, category: str, subcategory: str) -> AttributeSchema | None:
    return db.scalar(
        select(AttributeSchema).where(
            AttributeSchema.category == category,
            AttributeSchema.subcategory == subcategory,
        )
    )


def get_schema(db: Session, category: str, subcategory: str | None) -> list[dict]:
    """Return the attribute field defs for a category/subcategory."""
    if not category:
        return []
    sub = (subcategory or "").strip()

    # 1) Cache hit
    cached = _get_cached(db, category, sub)
    if cached and cached.schema:
        return cached.schema

    # 2) Groq generation (cached to DB)
    if settings.groq_enabled:
        try:
            generated = groq_service.generate_attribute_schema(category, sub or None)
            if generated:
                row = cached or AttributeSchema(category=category, subcategory=sub)
                row.schema = generated
                row.source = "ai"
                db.add(row)
                db.commit()
                return generated
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Attribute schema generation failed for %s/%s (%s); using builtin.",
                category, sub, exc,
            )

    # 3) Builtin fallback (not persisted, so a later AI run can replace it)
    return _builtin(category)
