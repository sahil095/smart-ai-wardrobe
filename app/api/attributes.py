"""Category-dependent attribute schema API (Phase 1)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import attribute_service

router = APIRouter(prefix="/api/attributes", tags=["attributes"])


@router.get("/schema")
def get_attribute_schema(
    category: str,
    subcategory: str | None = None,
    db: Session = Depends(get_db),
):
    """Return the filterable attribute field defs for a category/subcategory."""
    fields = attribute_service.get_schema(db, category, subcategory)
    return {"category": category, "subcategory": subcategory or "", "fields": fields}
