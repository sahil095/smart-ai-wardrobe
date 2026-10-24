"""Category-dependent attribute schemas.

Resolution order for a (category, subcategory):
1. Curated schema (category, then subcategory). This is the form people see.
2. DB cache from an earlier Groq run, for a category we have not curated.
3. Groq generation (if configured) -> cached to DB.
4. Empty list.

Curated schemas win even when an old AI cache exists. Those cached schemas
were told to skip pattern, material, fit, sleeve, and neck, which are now
part of the dynamic filters.

Returns field defs: {key, label, type:'select'|'text', options?, help?}.
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import constants
from app.config import settings
from app.models import AttributeSchema
from app.services import groq_service

logger = logging.getLogger(__name__)


def _get_cached(db: Session, category: str, subcategory: str) -> AttributeSchema | None:
    return db.scalar(
        select(AttributeSchema).where(
            AttributeSchema.category == category,
            AttributeSchema.subcategory == subcategory,
        )
    )


def _with_help(fields: list[dict]) -> list[dict]:
    out = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        item = dict(field)
        help_text = str(item.get("help") or "").strip()
        if not help_text and item.get("label"):
            help_text = f"Pick the {str(item['label']).lower()} that best matches this item."
        if help_text:
            item["help"] = help_text[:160]
        out.append(item)
    return out


def get_schema(db: Session, category: str, subcategory: str | None) -> list[dict]:
    """Return the attribute field defs for a category/subcategory."""
    if not category:
        return []
    sub = (subcategory or "").strip()

    curated = constants.attribute_schema(category, sub or None)
    if curated:
        return _with_help(curated)

    cached = _get_cached(db, category, sub)
    if cached and cached.schema:
        return _with_help(cached.schema)

    if settings.groq_enabled:
        try:
            generated = groq_service.generate_attribute_schema(category, sub or None)
            if generated:
                row = cached or AttributeSchema(category=category, subcategory=sub)
                row.schema = generated
                row.source = "ai"
                db.add(row)
                db.commit()
                return _with_help(generated)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Attribute schema generation failed for %s/%s (%s).",
                category, sub, exc,
            )

    return []


def promote_columns(data: dict) -> None:
    """Copy dynamic filter values onto the matching item columns.

    A missing key means that filter does not apply, so the column is cleared.
    Skipped when ``attributes`` was not part of this write.
    """
    if "attributes" not in data or data["attributes"] is None:
        return
    attrs = data["attributes"] or {}
    for key, column in constants.PROMOTED_ATTRIBUTE_COLUMNS.items():
        raw = attrs.get(key)
        if isinstance(raw, str):
            raw = raw.strip()
        data[column] = raw or None


def read_attribute(item, key: str) -> str:
    """Value for a dynamic filter, falling back to the older column."""
    attrs = getattr(item, "attributes", None) or {}
    raw = attrs.get(key)
    if raw not in (None, "", []):
        return str(raw)
    column = constants.PROMOTED_ATTRIBUTE_COLUMNS.get(key)
    if column:
        raw = getattr(item, column, None)
        if raw not in (None, "", []):
            return str(raw)
    return ""
