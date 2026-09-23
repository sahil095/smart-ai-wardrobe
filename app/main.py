"""Wardrobe AI — FastAPI application entrypoint."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import attributes, meta, outfits, users, wardrobe, weather
from app.config import settings
from app.database import init_db

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Ensure local upload dir exists (used when Cloudinary is not configured).
(STATIC_DIR / "uploads").mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Wardrobe AI", version="1.0.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# API routers
app.include_router(users.router)
app.include_router(wardrobe.router)
app.include_router(weather.router)
app.include_router(outfits.router)
app.include_router(meta.router)
app.include_router(attributes.router)


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    """Serve the service worker from the root so its scope covers the whole app."""
    return FileResponse(
        STATIC_DIR / "js" / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    """Serve the PWA manifest with the correct MIME type."""
    return FileResponse(
        STATIC_DIR / "manifest.webmanifest",
        media_type="application/manifest+json",
    )


@app.get("/health", tags=["meta"])
def health():
    return {
        "status": "ok",
        "groq_enabled": settings.groq_enabled,
        "cloudinary_enabled": settings.cloudinary_enabled,
        "outfit_count": settings.outfit_count,
    }


# ---- Page routes (server-rendered shells; Alpine.js drives interactivity) ----

def _page(request: Request, template: str, active: str, **ctx) -> HTMLResponse:
    return templates.TemplateResponse(
        template,
        {"request": request, "active": active, "outfit_count": settings.outfit_count, **ctx},
    )


@app.get("/", response_class=HTMLResponse)
def splash(request: Request):
    return _page(request, "index.html", active="home")


@app.get("/profile", response_class=HTMLResponse)
def profile(request: Request):
    return _page(request, "profile.html", active="profile")


@app.get("/wardrobe", response_class=HTMLResponse)
def wardrobe_page(request: Request):
    return _page(request, "wardrobe.html", active="wardrobe")


@app.get("/add", response_class=HTMLResponse)
def add_item_page(request: Request):
    return _page(request, "add_item.html", active="add")


@app.get("/generator", response_class=HTMLResponse)
def generator_page(request: Request):
    return _page(request, "generator.html", active="generator")


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    return _page(request, "history.html", active="history")
