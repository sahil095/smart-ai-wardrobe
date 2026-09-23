"""Wardrobe item CRUD + image upload API."""
import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, WardrobeItem
from app.schemas import WardrobeItemCreate, WardrobeItemOut, WardrobeItemUpdate
from app.services import image_service

router = APIRouter(prefix="/api/wardrobe", tags=["wardrobe"])


@router.get("", response_model=list[WardrobeItemOut])
def list_items(
    user_id: int,
    category: str | None = None,
    color: str | None = None,
    season: str | None = None,
    laundry_status: str | None = None,
    favorites_only: bool = False,
    search: str | None = None,
    attrs: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(WardrobeItem).where(WardrobeItem.user_id == user_id)
    if category:
        stmt = stmt.where(WardrobeItem.category == category)
    if laundry_status:
        stmt = stmt.where(WardrobeItem.laundry_status == laundry_status)
    if favorites_only:
        stmt = stmt.where(WardrobeItem.favorite.is_(True))
    if color:
        like = f"%{color}%"
        stmt = stmt.where(
            (WardrobeItem.primary_color.ilike(like))
            | (WardrobeItem.secondary_color.ilike(like))
        )
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            (WardrobeItem.name.ilike(like)) | (WardrobeItem.brand.ilike(like))
        )
    stmt = stmt.order_by(WardrobeItem.created_at.desc())

    items = db.scalars(stmt).all()

    # Season is a JSON list; filter in Python so it works on SQLite and MySQL.
    if season:
        items = [i for i in items if season in (i.season or [])]

    # Attribute facets: `attrs` is a JSON object of {key: value}; match all.
    if attrs:
        try:
            wanted = json.loads(attrs)
        except (ValueError, TypeError):
            wanted = {}
        if isinstance(wanted, dict):
            wanted = {k: v for k, v in wanted.items() if v not in (None, "", [])}
            if wanted:
                items = [
                    i
                    for i in items
                    if all(
                        str((i.attributes or {}).get(k, "")) == str(v)
                        for k, v in wanted.items()
                    )
                ]
    return items


@router.post("", response_model=WardrobeItemOut, status_code=status.HTTP_201_CREATED)
def create_item(payload: WardrobeItemCreate, db: Session = Depends(get_db)):
    if not db.get(User, payload.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    item = WardrobeItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{item_id}", response_model=WardrobeItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(WardrobeItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.put("/{item_id}", response_model=WardrobeItemOut)
def update_item(
    item_id: int, payload: WardrobeItemUpdate, db: Session = Depends(get_db)
):
    item = db.get(WardrobeItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(WardrobeItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    image_service.delete_local_image(item.image_url)
    db.delete(item)
    db.commit()


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """Upload an image and return the original + standardized display URLs.

    Cloudinary uploads also return a background-removed, padded ``display_image_url``
    (a "retail PDP" look). Local fallback returns the same URL for both.
    """
    try:
        result = await image_service.save_image(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except image_service.ImageUploadError as exc:
        # Transient upstream/network failure reaching Cloudinary.
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return result
