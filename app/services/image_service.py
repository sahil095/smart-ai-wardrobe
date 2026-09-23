"""Image storage service.

Uploads to Cloudinary when credentials are configured; otherwise falls back
to saving files locally under app/static/uploads and returning a served URL.
Only the resulting URL/path is persisted in the database (per PRD).
"""
import logging
import os
import time
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

logger = logging.getLogger(__name__)


class ImageUploadError(Exception):
    """Raised when an image cannot be uploaded to the image host."""

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


def _aspect_dims(aspect: str, long_side: int = 1000) -> tuple[int, int]:
    """Convert an aspect like '1:1' or '3:4' into concrete pixel dimensions."""
    try:
        w_s, h_s = (aspect or "1:1").split(":")
        wr, hr = float(w_s), float(h_s)
        if wr <= 0 or hr <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        wr, hr = 1.0, 1.0
    if wr >= hr:
        return long_side, max(1, int(round(long_side * hr / wr)))
    return max(1, int(round(long_side * wr / hr))), long_side


def build_display_url(public_id: str) -> str:
    """Build a standardized "retail PDP" display URL via on-the-fly transforms.

    Chain:
    1. Remove the original background (leaves transparency).
    2. Fill that transparency with a solid brand color — pad alone only
       colors letterbox bars, not the cutout's transparent pixels.
    3. Pad to a fixed canvas so every item sits on the same square.
    4. Auto quality. Format stays PNG-capable until the solid fill is applied
       so ``f_auto`` does not flatten transparency to black first.
    """
    _ensure_cloudinary()
    import cloudinary

    bg = f"rgb:{settings.image_bg_color}"
    width, height = _aspect_dims(settings.image_aspect)
    transformation = [
        {"effect": "background_removal"},
        {"background": bg},
        {"width": width, "height": height, "crop": "pad", "background": bg},
        {"quality": "auto", "fetch_format": "auto"},
    ]
    return cloudinary.CloudinaryImage(public_id).build_url(
        transformation=transformation, secure=True
    )


def _upload_to_cloudinary(contents: bytes, *, attempts: int = 3) -> dict:
    """Upload bytes to Cloudinary with a timeout and retry/backoff.

    Cloudinary/network hiccups (e.g. RemoteDisconnected, connection resets) are
    usually transient, so we retry a few times before giving up.
    """
    _ensure_cloudinary()
    import cloudinary.uploader

    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return cloudinary.uploader.upload(
                contents,
                folder="wardrobe_ai",
                resource_type="image",
                timeout=30,
            )
        except Exception as exc:  # noqa: BLE001 - network + cloudinary errors
            last_exc = exc
            logger.warning(
                "Cloudinary upload attempt %d/%d failed: %s", attempt, attempts, exc
            )
            if attempt < attempts:
                time.sleep(0.5 * (2 ** (attempt - 1)))  # 0.5s, 1s, 2s ...
    raise ImageUploadError(
        "Couldn't reach Cloudinary after several attempts. Please check your "
        "internet connection (and Cloudinary status), then try uploading again."
    ) from last_exc


async def save_image(file: UploadFile) -> dict:
    """Persist an uploaded image.

    Returns a dict: ``{"image_url", "display_image_url", "public_id"}``.
    When Cloudinary is configured, ``display_image_url`` is a standardized
    (background-removed, padded) variant. Otherwise it falls back to the
    original local URL.
    """
    ext = _validate(file)
    contents = await file.read()

    if settings.cloudinary_enabled:
        result = _upload_to_cloudinary(contents)
        image_url = result["secure_url"]
        public_id = result.get("public_id")
        display_url = image_url
        if settings.standardize_images and public_id:
            try:
                display_url = build_display_url(public_id)
            except Exception:  # noqa: BLE001 - never fail upload over a transform
                display_url = image_url
        return {
            "image_url": image_url,
            "display_image_url": display_url,
            "public_id": public_id,
        }

    # Local fallback (no standardization available)
    LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = LOCAL_UPLOAD_DIR / filename
    with open(dest, "wb") as f:
        f.write(contents)
    url = f"/static/uploads/{filename}"
    return {"image_url": url, "display_image_url": url, "public_id": None}


def public_id_from_url(image_url: str | None) -> str | None:
    """Best-effort extraction of a Cloudinary public_id from a delivery URL.

    e.g. https://res.cloudinary.com/<cloud>/image/upload/v123/wardrobe_ai/abc.jpg
    -> "wardrobe_ai/abc". Returns None for non-Cloudinary URLs.
    """
    if not image_url or "res.cloudinary.com" not in image_url:
        return None
    try:
        after = image_url.split("/upload/", 1)[1]
        # Drop a leading version segment like "v1699999999/"
        parts = after.split("/")
        if parts and parts[0].startswith("v") and parts[0][1:].isdigit():
            parts = parts[1:]
        path = "/".join(parts)
        # Strip file extension
        if "." in path.rsplit("/", 1)[-1]:
            path = path.rsplit(".", 1)[0]
        return path or None
    except (IndexError, ValueError):
        return None


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
