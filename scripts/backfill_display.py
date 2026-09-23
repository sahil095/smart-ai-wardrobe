"""Backfill display_image_url / image_public_id for pre-existing items.

Derives the Cloudinary public_id from each item's stored image_url and builds
the standardized display URL. Safe to re-run (skips items already populated or
without a Cloudinary URL).

Run from the project root:  python -m scripts.backfill_display
"""
from app.config import settings
from app.database import SessionLocal, init_db
from app.models import WardrobeItem
from app.services import image_service


def run():
    init_db()
    if not settings.cloudinary_enabled:
        print("Cloudinary not configured — nothing to backfill.")
        return

    db = SessionLocal()
    updated = 0
    try:
        items = db.query(WardrobeItem).all()
        for item in items:
            if item.display_image_url and item.display_image_url != item.image_url:
                continue  # already standardized
            public_id = item.image_public_id or image_service.public_id_from_url(
                item.image_url
            )
            if not public_id:
                continue  # local or non-Cloudinary image
            try:
                item.image_public_id = public_id
                item.display_image_url = image_service.build_display_url(public_id)
                updated += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  ! item {item.id} failed: {exc}")
        db.commit()
        print(f"Backfilled {updated} item(s).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
