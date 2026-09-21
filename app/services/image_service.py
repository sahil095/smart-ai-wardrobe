"""Image storage service.

Uploads to Cloudinary when credentials are configured; otherwise falls back
to saving files locally under app/static/uploads and returning a served URL.
Only the resulting URL/path is persisted in the database (per PRD).
"""
import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

LOCAL_UPLOAD_DIR = Path(__file__).resolve().parent.parent / "static" / "uploads"

_cloudinary_ready = False


def _ensure_cloudinary():
    global _cloudinary_ready
    if _cloudinary_ready:
        return
    import cloudinary  # imported lazily

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )
    _cloudinary_ready = True


def _validate(file: UploadFile) -> str:
    ext = ALLOWED_CONTENT_TYPES.get((file.content_type or "").lower())
    if not ext:
        # Fall back to file extension if content-type is missing/unknown.
        suffix = Path(file.filename or "").suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            return ".jpg" if suffix == ".jpeg" else suffix
        raise ValueError(
            "Unsupported image format. Use JPG, PNG, WEBP or GIF."
        )
    return ext


async def save_image(file: UploadFile) -> str:
    """Persist an uploaded image and return its accessible URL/path."""
    ext = _validate(file)
    contents = await file.read()

    if settings.cloudinary_enabled:
        _ensure_cloudinary()
        import cloudinary.uploader

        result = cloudinary.uploader.upload(
            contents, folder="wardrobe_ai", resource_type="image"
        )
        return result["secure_url"]

    # Local fallback
    LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = LOCAL_UPLOAD_DIR / filename
    with open(dest, "wb") as f:
        f.write(contents)
    return f"/static/uploads/{filename}"


def delete_local_image(image_url: str | None) -> None:
    """Best-effort removal of a locally-stored image."""
    if not image_url or not image_url.startswith("/static/uploads/"):
        return
    filename = image_url.rsplit("/", 1)[-1]
    path = LOCAL_UPLOAD_DIR / filename
    try:
        if path.exists():
            os.remove(path)
    except OSError:
        pass
