"""Wardrobe AI — FastAPI application entrypoint."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.api import attributes, auth, meta, outfits, stylist, users, wardrobe, weather
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

_PUBLIC_EXACT = {
    "/login",
    "/health",
    "/sw.js",
    "/manifest.webmanifest",
    "/api/auth/status",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/claim",
}


@app.middleware("http")
async def require_sign_in(request: Request, call_next):
    path = request.url.path
    if (
        path.startswith("/static/")
        or path in _PUBLIC_EXACT
        or request.session.get("user_id")
    ):
        if path == "/login" and request.session.get("user_id"):
            return RedirectResponse("/", status_code=303)
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"detail": "Sign in required"}, status_code=401)
    return RedirectResponse("/login", status_code=303)


# SessionMiddleware is added last so it runs first and request.session exists.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=False,
    max_age=60 * 60 * 24 * 30,
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# API routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(wardrobe.router)
app.include_router(weather.router)
app.include_router(outfits.router)
app.include_router(meta.router)
app.include_router(attributes.router)
app.include_router(stylist.router)


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
        "pixabay_enabled": settings.pixabay_enabled,
        "pexels_enabled": settings.pexels_enabled,
        "outfit_count": settings.outfit_count,
    }


# ---- Page routes (server-rendered shells; Alpine.js drives interactivity) ----

def _page(request: Request, template: str, active: str, **ctx) -> HTMLResponse:
    return templates.TemplateResponse(
        template,
        {"request": request, "active": active, "outfit_count": settings.outfit_count, **ctx},
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


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


@app.get("/gaps", response_class=HTMLResponse)
def gaps_page(request: Request):
    return _page(request, "gaps.html", active="home")


@app.get("/stylist", response_class=HTMLResponse)
def stylist_page(request: Request):
    return _page(request, "stylist.html", active="home")


@app.get("/ideas", response_class=HTMLResponse)
def ideas_page(request: Request):
    return _page(request, "ideas.html", active="wardrobe")
